"""
Phase 7 - Prepare the four modelling tables (Master Plan, section 6, Phase 7).

Run from the project root:   python ml/prepare_tables.py

Reads : data/processed/crimes_features.parquet
Writes: data/processed/coordinates.parquet   (K-Means)
        data/processed/area_day.parquet      (Multiple Regression)
        data/processed/incidents.parquet     (Decision Tree)
        data/processed/categorical.parquet   (Apriori, one-hot encoded)

It never modifies the source file or notebooks 01-04.
"""
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
SEED = 42
SAMPLE_N = 150_000            # Master Plan: 1-2 lakh rows for K-Means and Apriori
TRAIN_END_YEAR = 2024         # train 2023-2024, test 2025 onwards


def header(t):
    print("\n" + "=" * 70 + f"\n{t}\n" + "=" * 70)


def split_label(year):
    return np.where(year <= TRAIN_END_YEAR, "train", "test")


# ---------------------------------------------------------------- load
df = pd.read_parquet(PROC / "crimes_features.parquet")
df["date"] = pd.to_datetime(df["date"])
print("Loaded crimes_features:", df.shape,
      "|", df["date"].min().date(), "to", df["date"].max().date())

# ------------------------------------------------- 1. coordinates (K-Means)
header("1. coordinates.parquet  (K-Means)")
c = df[(df["has_coordinates"] == 1) & df["latitude"].notna() & df["longitude"].notna()]
print("Rows with valid coordinates:", len(c), "| dropped:", len(df) - len(c))
c = c.sample(n=min(SAMPLE_N, len(c)), random_state=SEED)
# K-Means uses lat/long only; the other columns are kept for profiling clusters
coords = c[["latitude", "longitude", "primary_type", "crime_group",
            "community_area", "district", "date"]].reset_index(drop=True)
coords.to_parquet(PROC / "coordinates.parquet", index=False)
print("Saved:", coords.shape, "| missing:", int(coords.isna().sum().sum()))

# ------------------------------------------ 2. area-day (Multiple Regression)
header("2. area_day.parquet  (Multiple Regression)")
areas = np.sort(df["community_area"].unique())
days = pd.date_range(df["date"].min(), df["date"].max(), freq="D")
print(f"{len(areas)} community areas x {len(days)} days = {len(areas)*len(days):,} grid rows")
if len(areas) != 77:
    print("WARNING: expected 77 community areas, found", len(areas), "-> check:", areas.tolist())

grid = pd.MultiIndex.from_product([areas, days], names=["community_area", "date"]).to_frame(index=False)
counts = df.groupby(["community_area", "date"]).size().rename("crime_count").reset_index()
ad = grid.merge(counts, on=["community_area", "date"], how="left")
ad["crime_count"] = ad["crime_count"].fillna(0).astype(int)   # zero-crime days
print(f"Zero-crime area-days: {(ad['crime_count']==0).sum():,} "
      f"({(ad['crime_count']==0).mean()*100:.1f}%)")

# History features: built per area, strictly from PAST days (no same-day leakage)
ad = ad.sort_values(["community_area", "date"]).reset_index(drop=True)
g = ad.groupby("community_area")["crime_count"]
ad["lag_1"] = g.shift(1)
ad["lag_7"] = g.shift(7)
ad["lag_30"] = g.shift(30)
ad["rolling_7"] = g.transform(lambda s: s.shift(1).rolling(7).mean())
ad["rolling_30"] = g.transform(lambda s: s.shift(1).rolling(30).mean())

# Calendar + weather: one value per date
daily = (df.groupby("date")[["temperature", "rainfall", "is_holiday", "is_new_year"]]
           .first().reset_index())
ad = ad.merge(daily, on="date", how="left")
ad["day_of_week"] = ad["date"].dt.dayofweek.astype("int32")
ad["month"] = ad["date"].dt.month.astype("int32")
ad["year"] = ad["date"].dt.year.astype("int32")
ad["is_weekend"] = (ad["day_of_week"] >= 5).astype(int)

# Socio-economic: one value per community area
socio_cols = ["population", "poverty_rate", "unemployment", "per_capita_income",
              "hardship_index", "pct_no_diploma", "pct_crowded", "pct_dependent"]
socio = df.groupby("community_area")[socio_cols].first().reset_index()
ad = ad.merge(socio, on="community_area", how="left")

# First 30 days of each area have no full history -> drop them
before = len(ad)
ad = ad.dropna(subset=["lag_1", "lag_7", "lag_30", "rolling_7", "rolling_30"]).reset_index(drop=True)
print(f"Dropped {before-len(ad):,} warm-up rows (first 30 days per area)")
ad["split"] = split_label(ad["year"])
for col in ["lag_1", "lag_7", "lag_30"]:
    ad[col] = ad[col].astype(int)
ad.to_parquet(PROC / "area_day.parquet", index=False)
print("Saved:", ad.shape)
print("Split:", ad["split"].value_counts().to_dict())
miss = ad.isna().sum()
print("Missing values:", miss[miss > 0].to_dict() or "none")

# ---------------------------------------------- 3. incidents (Decision Tree)
header("3. incidents.parquet  (Decision Tree)")
inc = df[df["time_unknown"] == 0]
print(f"Excluded {len(df)-len(inc):,} unknown-time records (hour is unreliable)")
inc = inc[["is_violent", "hour", "day_of_week", "season", "location_group",
           "domestic", "community_area", "district",
           "month", "year", "date"]].copy()          # month/year/date: not features, kept for the website + split
inc["split"] = split_label(inc["year"])
inc = inc.reset_index(drop=True)
inc.to_parquet(PROC / "incidents.parquet", index=False)
print("Saved:", inc.shape, "| violent share: %.1f%%" % (inc["is_violent"].mean() * 100))
print("Split:", inc["split"].value_counts().to_dict())
miss = inc.isna().sum()
print("Missing values:", miss[miss > 0].to_dict() or "none")

# ------------------------------------------------ 4. categorical (Apriori)
header("4. categorical.parquet  (Apriori, one-hot)")
cat_src = df[df["time_unknown"] == 0]
cat_src = cat_src.sample(n=min(SAMPLE_N, len(cat_src)), random_state=SEED)
cat = pd.DataFrame({
    "time_of_day": cat_src["time_of_day"].astype(str),
    "location_group": cat_src["location_group"].astype(str),
    "crime_group": cat_src["crime_group"].astype(str),
    "season": cat_src["season"].astype(str),
    "is_weekend": np.where(cat_src["is_weekend"] == 1, "weekend", "weekday"),
    "district": "D" + cat_src["district"].astype(int).astype(str).str.zfill(2),
})
onehot = pd.get_dummies(cat, prefix_sep="=").astype(bool).reset_index(drop=True)
onehot.to_parquet(PROC / "categorical.parquet", index=False)
print("Saved:", onehot.shape, "(rows x one-hot columns)")
print("Example columns:", onehot.columns[:8].tolist())

header("DONE - four modelling tables written to data/processed/")
