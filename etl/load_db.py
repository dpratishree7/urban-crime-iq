import os
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
engine = create_engine(os.getenv("DATABASE_URL"), pool_pre_ping=True)

df = pd.read_parquet(ROOT / "data/processed/crimes_features.parquet")
df["location_description"] = df["location_description"].fillna("UNKNOWN")

# ---------- dim_date ----------
dim_date = df.drop_duplicates("date")[
    ["date", "year", "month", "day_of_week", "season",
     "is_weekend", "is_holiday", "is_new_year"]].copy()
dim_date["date_key"] = dim_date["date"].dt.strftime("%Y%m%d").astype(int)
dim_date["day"] = dim_date["date"].dt.day
dim_date["full_date"] = dim_date["date"].dt.date
for c in ["is_weekend", "is_holiday", "is_new_year"]:
    dim_date[c] = dim_date[c].astype(bool)
dim_date = dim_date[["date_key", "full_date", "year", "month", "day",
                     "day_of_week", "season", "is_weekend", "is_holiday", "is_new_year"]]

# ---------- dim_location ----------
loc_keys = ["beat", "district", "ward", "community_area"]
area_cols = ["area_name", "population", "poverty_rate", "unemployment",
             "per_capita_income", "hardship_index", "pct_crowded",
             "pct_no_diploma", "pct_dependent"]
dim_location = df[loc_keys + area_cols].drop_duplicates(subset=loc_keys).copy()
dim_location["ward"] = dim_location["ward"].astype("Int64")

# ---------- dim_crime_type ----------
ct_cols = ["iucr", "primary_type", "description", "fbi_code", "crime_group", "is_violent"]
dim_crime_type = df[ct_cols].drop_duplicates().copy()
dim_crime_type["is_violent"] = dim_crime_type["is_violent"].astype(bool)

# ---------- dim_location_type ----------
dim_location_type = df[["location_description", "location_group"]].drop_duplicates().copy()

# ---------- check text lengths against the schema ----------
limits = [(dim_location, "beat", 4), (dim_location, "area_name", 60),
          (dim_crime_type, "iucr", 4), (dim_crime_type, "primary_type", 40),
          (dim_crime_type, "description", 80), (dim_crime_type, "fbi_code", 4),
          (dim_crime_type, "crime_group", 30),
          (dim_location_type, "location_description", 80),
          (dim_location_type, "location_group", 15)]
for frame, col, limit in limits:
    longest = frame[col].astype(str).str.len().max()
    print(f"{col}: longest {longest} (limit {limit})")
    assert longest <= limit, f"{col} is too long for the schema"

# ---------- load ----------
with engine.begin() as conn:
    conn.execute(text("TRUNCATE fact_crime, dim_date, dim_location, "
                      "dim_crime_type, dim_location_type RESTART IDENTITY CASCADE"))

tables = [("dim_date", dim_date), ("dim_location", dim_location),
          ("dim_crime_type", dim_crime_type), ("dim_location_type", dim_location_type)]
for name, frame in tables:
    frame.to_sql(name, engine, if_exists="append", index=False,
                 chunksize=1000, method="multi")
    print(f"Loaded {name}: {len(frame):,} rows")

with engine.connect() as conn:
    for name, _ in tables:
        n = conn.execute(text(f"SELECT COUNT(*) FROM {name}")).scalar()
        print(f"In database {name}: {n:,}")