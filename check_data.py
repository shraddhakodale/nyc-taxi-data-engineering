import pandas as pd

file_path = r"data\2025\yellow_tripdata_2025-01.parquet"

df = pd.read_parquet(file_path)

print("Total rows:", len(df))
print("\nColumns:")
print(df.columns.tolist())

print("\nFirst 5 rows:")
print(df.head())

print("\nData types:")
print(df.dtypes)
