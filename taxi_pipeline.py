import gzip
import shutil
import urllib.request

url = "https://github.com/DataTalksClub/nyc-tlc-data/releases/download/yellow/yellow_tripdata_2021-01.csv.gz"

gz_file = "yellow_tripdata_2021-01.csv.gz"
csv_file = "yellow_tripdata_2021-01.csv"

print("Downloading taxi data...")

urllib.request.urlretrieve(url, gz_file)

print("Download completed.")

print("Extracting CSV...")

with gzip.open(gz_file, "rb") as f_in:
    with open(csv_file, "wb") as f_out:
        shutil.copyfileobj(f_in, f_out)

print("Extraction completed.")
print(f"CSV file created: {csv_file}")

import pandas as pd
from sqlalchemy import create_engine

print("Loading CSV into PostgreSQL...")

df = pd.read_csv(csv_file)

print(f"CSV rows: {len(df)}")

engine = create_engine(
    "postgresql+psycopg2://root:root@localhost:5432/ny_taxi"
)

df.head(0).to_sql(
    "yellow_taxi_data",
    engine,
    if_exists="replace",
    index=False
)

df.to_sql(
    "yellow_taxi_data",
    engine,
    if_exists="append",
    index=False,
    chunksize=10000
)

print("Data loaded successfully into PostgreSQL!")
print(f"Total rows: {len(df)}")