"""Re-creates EDA charts 07 and 08 with fixes. Run from project root:  python ml/make_eda_fixes.py
07: violent vs non-violent by hour  (+ time_unknown note)
08: violent vs non-violent by season (average crimes per month, partial month excluded)
"""
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "screenshots"
df = pd.read_parquet(ROOT / "data" / "processed" / "crimes_features.parquet",
                     columns=["date", "hour", "time_unknown", "is_violent", "season"])
df["date"] = pd.to_datetime(df["date"])
df["kind"] = df["is_violent"].map({0: "Non-violent", 1: "Violent"})

# ---- 07: by hour, known times only
known = df[df["time_unknown"] == 0]
n_unknown = int((df["time_unknown"] == 1).sum())
h = known.groupby(["hour", "kind"]).size().unstack(fill_value=0)
fig, ax = plt.subplots(figsize=(11, 5))
h.plot(ax=ax, marker="o")
ax.set_xticks(range(24))
ax.set_title("Violent vs Non-violent Crimes by Hour (known times only)")
ax.set_xlabel("Hour of day"); ax.set_ylabel("Number of crimes")
fig.text(0.01, -0.02,
         f"Note: {n_unknown:,} records with unknown time (default 00:00 / 12:00 stamps) are excluded.\n"
         "Genuine crimes at these hours were also flagged, so hour 12 (and 0) are understated and the dip at noon is an artefact.",
         fontsize=8, va="top")
fig.savefig(OUT / "07_violent_by_hour.png", dpi=150, bbox_inches="tight")
plt.close(fig)
print("Saved 07_violent_by_hour.png | unknown-time records excluded:", f"{n_unknown:,}")

# ---- 08: by season, average per month (complete months only)
last = df["date"].max()
full = df[~((df["date"].dt.year == last.year) & (df["date"].dt.month == last.month))].copy()
full["ym"] = full["date"].dt.to_period("M")
months_per_season = full.groupby("season")["ym"].nunique()
cnt = full.groupby(["season", "kind"]).size().unstack(fill_value=0)
avg = cnt.div(months_per_season, axis=0)
order = [s for s in ["WINTER", "SPRING", "SUMMER", "FALL"] if s in avg.index]
avg = avg.loc[order]
fig, ax = plt.subplots(figsize=(8, 5))
avg.plot(kind="bar", ax=ax)
ax.set_title("Average Crimes per Month by Season (complete months only)")
ax.set_ylabel("Average crimes per month"); ax.set_xlabel("")
plt.xticks(rotation=0)
fig.savefig(OUT / "08_violent_by_season.png", dpi=150, bbox_inches="tight")
plt.close(fig)
print("Saved 08_violent_by_season.png")
print("\nMonths per season used:", months_per_season.loc[order].to_dict())
print("Excluded partial month:", last.strftime("%Y-%m"))
print("\nAverage crimes per month:\n", avg.round(0).astype(int).to_string())
