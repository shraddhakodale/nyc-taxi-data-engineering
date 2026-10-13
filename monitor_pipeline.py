
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
    rows_checked = 0
    issue_count = 0
    unique_affected = 0
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
            raise RuntimeError(
                result.stderr.strip() or "Quality check failed"
            )

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
            raise RuntimeError("Total records missing or zero")

        issue_count = sum(
            value
            for label, value in counts.items()
            if label != "Total records"
        )

        # Count distinct rows matching at least one selected rule.
        conn = connect_db()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT COUNT(*)
                    FROM yellow_taxi_data_2025
                    WHERE
                        tpep_pickup_datetime IS NULL
                        OR tpep_dropoff_datetime IS NULL
                        OR pulocationid IS NULL
                        OR dolocationid IS NULL
                        OR trip_distance IS NULL
                        OR trip_distance < 0
                        OR fare_amount < 0
                        OR total_amount < 0
                        OR trip_distance = 0
                        OR fare_amount <= -100
                        OR payment_type NOT IN (0, 1, 2, 3, 4)
                        OR payment_type IS NULL
                        OR (
                            tpep_pickup_datetime IS NOT NULL
                            AND tpep_dropoff_datetime IS NOT NULL
                            AND tpep_dropoff_datetime < tpep_pickup_datetime
                        )
                    """
                )
                unique_affected = cur.fetchone()[0]
        finally:
            conn.close()

        status = "CHECK_ISSUES" if issue_count else "SUCCESS"

    except Exception as exc:
        error_message = str(exc)
        print(f"Monitoring error: {error_message}")

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
        print(
            "Issue occurrences (overlapping checks): "
            f"{issue_count:,}"
        )
        print(
            "Unique affected records (selected rules): "
            f"{unique_affected:,}"
        )
    finally:
        conn.close()

    if status == "FAILED":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
