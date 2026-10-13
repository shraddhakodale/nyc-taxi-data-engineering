import os
import psycopg2

TABLE = "yellow_taxi_data_2025"

def main():
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        dbname=os.getenv("DB_NAME", "ny_taxi"),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", "root"),
        connect_timeout=10,
    )

    try:
        # Safety: this connection is read-only.
        conn.set_session(readonly=True, autocommit=True)

        checks = {
            "Total records": "COUNT(*)",
            "Missing pickup timestamp": "COUNT(*) FILTER (WHERE tpep_pickup_datetime IS NULL)",
            "Missing dropoff timestamp": "COUNT(*) FILTER (WHERE tpep_dropoff_datetime IS NULL)",
            "Missing pickup location": "COUNT(*) FILTER (WHERE pulocationid IS NULL)",
            "Missing dropoff location": "COUNT(*) FILTER (WHERE dolocationid IS NULL)",
            "Missing trip distance": "COUNT(*) FILTER (WHERE trip_distance IS NULL)",
            "Negative trip distance": "COUNT(*) FILTER (WHERE trip_distance < 0)",
            "Negative fare amount": "COUNT(*) FILTER (WHERE fare_amount < 0)",
            "Negative total amount": "COUNT(*) FILTER (WHERE total_amount < 0)",
            "Dropoff before pickup": (
                "COUNT(*) FILTER (WHERE tpep_pickup_datetime IS NOT NULL "
                "AND tpep_dropoff_datetime IS NOT NULL "
                "AND tpep_dropoff_datetime < tpep_pickup_datetime)"
            ),
        }

        with conn.cursor() as cur:
            cur.execute(
                "SELECT " + ", ".join(checks.values()) + f" FROM {TABLE}"
            )
            values = cur.fetchone()

        print("\n=== NYC TAXI DATA QUALITY REPORT ===")
        print(f"Table: {TABLE}\n")

        for label, value in zip(checks.keys(), values):
            print(f"{label}: {value:,}")

        issues = sum(value for label, value in zip(checks.keys(), values)
                     if label != "Total records")

        print("\nOverall result:", "CHECK ISSUES" if issues else "BASIC CHECKS PASSED")
        print("Note: counts can overlap; this is a basic validation report.")

    finally:
        conn.close()

if __name__ == "__main__":
    main()
