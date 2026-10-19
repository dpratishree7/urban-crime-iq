"""Creates EDA charts 16-18. Run from the project root:  python ml/make_eda_extra.py"""
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "screenshots"
OUT.mkdir(parents=True, exist_ok=True)

d = pd.read_parquet(ROOT / "data" / "processed" / "crimes_features.parquet",
                    columns=["community_area", "area_name", "population", "poverty_rate",
                             "per_capita_income", "primary_type", "arrest"])
print("Loaded rows:", len(d))

# ---- A. Community areas ranked by crimes per 1,000 residents
area = (d.groupby(["community_area", "area_name"])
          .agg(population=("population", "first"),
               poverty_rate=("poverty_rate", "first"),
               per_capita_income=("per_capita_income", "first"),
               crimes=("arrest", "size"))
          .reset_index())
area["crimes_per_1000"] = area["crimes"] * 1000 / area["population"]
top = area.sort_values("crimes_per_1000").tail(15)
fig, ax = plt.subplots(figsize=(9, 6))
ax.barh(top["area_name"], top["crimes_per_1000"])
ax.set_title("Top 15 community areas by crimes per 1,000 residents (Jan 2023 - Sep 2026)")
ax.set_xlabel("Crimes per 1,000 residents")
fig.text(0.01, 0.005, "Note: The Loop ranks high because few people live there but many visit.", fontsize=8)
fig.savefig(OUT / "16_area_crime_rate.png", dpi=150, bbox_inches="tight")
plt.close(fig)
print("\nTop 5 areas by crimes per 1,000:")
print(area.sort_values("crimes_per_1000", ascending=False)[["area_name", "population", "crimes", "crimes_per_1000"]].head(5).round(1).to_string(index=False))

# ---- B. Arrest rate by crime type (types with 5,000+ crimes)
t = d.groupby("primary_type")["arrest"].agg(rate="mean", n="size")
t = t[t["n"] >= 5000].sort_values("rate")
fig, ax = plt.subplots(figsize=(9, 6))
ax.barh(t.index, t["rate"] * 100)
ax.set_title("Arrest rate by crime type (types with 5,000+ crimes)")
ax.set_xlabel("Arrested (%)")
fig.savefig(OUT / "17_arrest_rate_by_type.png", dpi=150, bbox_inches="tight")
plt.close(fig)
print("\nHighest and lowest arrest rates (%):")
print((t["rate"] * 100).round(1).iloc[[0, 1, 2, -3, -2, -1]].to_string())

# ---- C. Correlation: poverty, income and crime RATE (77 areas)
corr = area[["poverty_rate", "per_capita_income", "crimes_per_1000"]].corr()
fig, ax = plt.subplots(figsize=(5.5, 4.5))
sns.heatmap(corr, annot=True, fmt=".2f", cmap="coolwarm", center=0, ax=ax)
ax.set_title("Correlation across 77 community areas")
fig.savefig(OUT / "18_area_rate_correlation.png", dpi=150, bbox_inches="tight")
plt.close(fig)
print("\nCorrelation (77 areas):\n", corr.round(3).to_string())
print("\nAreas used:", len(area))
print("Saved: 16_area_crime_rate.png, 17_arrest_rate_by_type.png, 18_area_rate_correlation.png")
