
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
        # Read-only: this script does not modify taxi data.
        conn.set_session(readonly=True, autocommit=True)

        checks = {
            "Total records": "COUNT(*)",
            "Missing pickup timestamp": (
                "COUNT(*) FILTER (WHERE tpep_pickup_datetime IS NULL)"
            ),
            "Missing dropoff timestamp": (
                "COUNT(*) FILTER (WHERE tpep_dropoff_datetime IS NULL)"
            ),
            "Missing pickup location": (
                "COUNT(*) FILTER (WHERE pulocationid IS NULL)"
            ),
            "Missing dropoff location": (
                "COUNT(*) FILTER (WHERE dolocationid IS NULL)"
            ),
            "Missing trip distance": (
                "COUNT(*) FILTER (WHERE trip_distance IS NULL)"
            ),
            "Negative trip distance": (
                "COUNT(*) FILTER (WHERE trip_distance < 0)"
            ),
            "Negative fare amount": (
                "COUNT(*) FILTER (WHERE fare_amount < 0)"
            ),
            "Negative total amount": (
                "COUNT(*) FILTER (WHERE total_amount < 0)"
            ),
            "Zero-distance trips": (
                "COUNT(*) FILTER (WHERE trip_distance = 0)"
            ),
            "Zero-distance with negative fare": (
                "COUNT(*) FILTER (WHERE trip_distance = 0 AND fare_amount < 0)"
            ),
            "Large negative fares (<= -100)": (
                "COUNT(*) FILTER (WHERE fare_amount <= -100)"
            ),
            "Invalid payment type": (
                "COUNT(*) FILTER (WHERE payment_type NOT IN (0, 1, 2, 3, 4) "
                "OR payment_type IS NULL)"
            ),
            "Dropoff before pickup": (
                "COUNT(*) FILTER (WHERE tpep_pickup_datetime IS NOT NULL "
                "AND tpep_dropoff_datetime IS NOT NULL "
                "AND tpep_dropoff_datetime < tpep_pickup_datetime)"
            ),
        }

        with conn.cursor() as cur:
            query = "SELECT " + ", ".join(checks.values()) + f" FROM {TABLE}"
            cur.execute(query)
            values = cur.fetchone()

        print("\n=== NYC TAXI DATA QUALITY REPORT ===")
        print(f"Table: {TABLE}\n")

        for label, value in zip(checks.keys(), values):
            print(f"{label}: {value:,}")

        issues = sum(
            value
            for label, value in zip(checks.keys(), values)
            if label != "Total records"
        )

        print(
            "\nOverall result:",
            "CHECK ISSUES" if issues else "BASIC CHECKS PASSED",
        )
        print("Note: counts can overlap; this is a basic validation report.")

    finally:
        conn.close()


if __name__ == "__main__":
    main()

