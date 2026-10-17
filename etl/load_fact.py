import io
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
n = len(df)
print("Crimes to load:", f"{n:,}")

# ---------- date key (matches dim_date) ----------
df["date_key"] = df["date"].dt.strftime("%Y%m%d").astype(int)

# ---------- read the dimension keys back from the database ----------
d_loc = pd.read_sql("SELECT location_key, beat, district, ward, community_area FROM dim_location", engine)
d_ct = pd.read_sql("SELECT crime_type_key, iucr, primary_type, description, fbi_code, "
                   "crime_group, is_violent FROM dim_crime_type", engine)
d_lt = pd.read_sql("SELECT location_type_key, location_description, location_group "
                   "FROM dim_location_type", engine)

# a missing ward is matched as -1 on both sides, so the join is safe
df["ward_k"] = df["ward"].astype("Int64").fillna(-1).astype(int)
d_loc["ward_k"] = d_loc["ward"].astype("Int64").fillna(-1).astype(int)
d_loc = d_loc.drop(columns="ward")
df["is_violent"] = df["is_violent"].astype(bool)

df = df.merge(d_loc, on=["beat", "district", "ward_k", "community_area"],
              how="left", validate="many_to_one")
df = df.merge(d_ct, on=["iucr", "primary_type", "description", "fbi_code",
                        "crime_group", "is_violent"],
              how="left", validate="many_to_one")
df = df.merge(d_lt, on=["location_description", "location_group"],
              how="left", validate="many_to_one")

print("Rows after merges:", f"{len(df):,}")
for k in ["location_key", "crime_type_key", "location_type_key"]:
    print(f"Missing {k}:", df[k].isna().sum())
assert len(df) == n, "a join duplicated or lost rows"
assert df[["location_key", "crime_type_key", "location_type_key"]].notna().all().all(), \
    "some crimes could not be matched to a dimension row"

# ---------- build the fact table ----------
fact = pd.DataFrame({
    "crime_id": range(1, n + 1),
    "date_key": df["date_key"],
    "location_key": df["location_key"].astype(int),
    "crime_type_key": df["crime_type_key"].astype(int),
    "location_type_key": df["location_type_key"].astype(int),
    "hour": df["hour"],
    "arrest": df["arrest"].astype(bool),
    "domestic": df["domestic"].astype(bool),
    "latitude": df["latitude"],
    "longitude": df["longitude"],
    "temperature": df["temperature"],
    "rainfall": df["rainfall"],
})
cols = list(fact.columns)

# ---------- load with COPY in chunks of 100,000 rows ----------
raw = engine.raw_connection()
try:
    cur = raw.cursor()
    cur.execute("TRUNCATE fact_crime")
    raw.commit()
    CHUNK = 100_000
    for start in range(0, n, CHUNK):
        chunk = fact.iloc[start:start + CHUNK]
        buf = io.StringIO()
        chunk.to_csv(buf, index=False, header=False)
        buf.seek(0)
        cur.copy_expert(f"COPY fact_crime ({','.join(cols)}) FROM STDIN WITH (FORMAT csv)", buf)
        raw.commit()
        print(f"Loaded {min(start + CHUNK, n):,} / {n:,}")
finally:
    raw.close()

# ---------- verify and check the size against the 500 MB limit ----------
with engine.connect() as conn:
    print("Rows in fact_crime:", f"{conn.execute(text('SELECT COUNT(*) FROM fact_crime')).scalar():,}")
    print("fact_crime size:", conn.execute(text(
        "SELECT pg_size_pretty(pg_total_relation_size('fact_crime'))")).scalar())
    print("Whole database size:", conn.execute(text(
        "SELECT pg_size_pretty(pg_database_size(current_database()))")).scalar())