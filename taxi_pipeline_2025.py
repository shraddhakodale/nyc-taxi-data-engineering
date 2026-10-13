import os
import pandas as pd
import pyarrow.parquet as pq
from sqlalchemy import create_engine, URL

PARQUET_FILE = r"data\2025\yellow_tripdata_2025-01.parquet"
TABLE_NAME = "yellow_taxi_data_2025"

password = os.environ.get("DB_PASSWORD", "root")

url = URL.create(
    drivername="postgresql+psycopg2",
    username="root",
    password=password,
    host="localhost",
    port=5432,
    database="ny_taxi",
)

engine = create_engine(url)
parquet_file = pq.ParquetFile(PARQUET_FILE)

total_rows = 0
first_batch = True

print("Starting January 2025 taxi data pipeline...")
print("Total rows in source:", parquet_file.metadata.num_rows)

try:
    for batch in parquet_file.iter_batches(batch_size=50000):
        df = batch.to_pandas()

        # PostgreSQL-friendly lowercase column names
        df.columns = [col.lower() for col in df.columns]

        df.to_sql(
            TABLE_NAME,
            engine,
            if_exists="replace" if first_batch else "append",
            index=False,
            chunksize=10000,
            method="multi"
        )

        total_rows += len(df)
        first_batch = False

        print(f"Loaded rows: {total_rows:,}")

    print("\nPipeline completed successfully!")
    print("PostgreSQL table:", TABLE_NAME)
    print("Rows loaded:", f"{total_rows:,}")

except Exception as exc:
    print("\nPipeline failed:", exc)
    raise

finally:
    engine.dispose()
