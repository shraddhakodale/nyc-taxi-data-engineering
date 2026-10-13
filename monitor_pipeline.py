import os
import re
import subprocess
import sys
import psycopg2

PIPELINE_NAME = "nyc_taxi_data_quality"

def connect_db():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        dbname=os.getenv("DB_NAME", "ny_taxi"),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", "root"),
        connect_timeout=10,
    )

def main():
    started = False
    rows_checked = 0
    issue_count = 0
    status = "FAILED"
    error_message = None

    try:
        result = subprocess.run(
            [sys.executable, "data_quality.py"],
            capture_output=True,
            text=True,
            check=False,
        )
        report = result.stdout
        print(report, end="")

        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "Quality check failed")

        if "Total records:" not in report:
            raise RuntimeError("Could not parse the quality report")

        counts = {}
        for line in report.splitlines():
            match = re.match(r"^(.+):\s*([\d,]+)\s*$", line)
            if match:
                counts[match.group(1).strip()] = int(
                    match.group(2).replace(",", "")
                )

        rows_checked = counts.get("Total records", 0)
        if rows_checked == 0:
            raise RuntimeError("Total records missing or zero in report")

        issue_count = sum(
            value for label, value in counts.items()
            if label != "Total records"
        )
        status = "CHECK_ISSUES" if issue_count else "SUCCESS"

    except Exception as exc:
        error_message = str(exc)
        print(f"Monitoring error: {error_message}")

    # Save one monitoring record for this run.
    conn = connect_db()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO taxi_pipeline_runs
                        (pipeline_name, finished_at, status,
                         rows_checked, issue_count, error_message)
                    VALUES (%s, NOW(), %s, %s, %s, %s)
                    RETURNING run_id
                    """,
                    (
                        PIPELINE_NAME,
                        status,
                        rows_checked,
                        issue_count,
                        error_message,
                    ),
                )
                run_id = cur.fetchone()[0]
        print(f"\nMonitoring saved. Run ID: {run_id}")
        print(f"Status: {status}")
        print(f"Rows checked: {rows_checked:,}")
        print(f"Issue count (overlapping checks may be counted more than once): {issue_count:,}")
    finally:
        conn.close()

    if status == "FAILED":
        raise SystemExit(1)

if __name__ == "__main__":
    main()
