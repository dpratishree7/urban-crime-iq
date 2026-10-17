"""
Phase 8.2 - Multiple Regression (forecast crimes per community area per day).
Run from project root:   python ml/train_regression.py

Input : data/processed/area_day.parquet  (chronological 'split' column: train 2023-24, test 2025+)
Output: ml/models/regression.pkl                 both pipelines + feature lists
        ml/results/regression_metrics.csv        MAE / RMSE / R2 for all three models
        ml/results/regression_coefficients.csv   enhanced-model coefficients
        ml/results/regression_vif.csv            multicollinearity check
        ml/results/regression_test_predictions.csv
        docs/screenshots/12_regression_actual_vs_predicted.png

Models compared on the TEST period:
  1. Naive baseline  : same as last week (lag_7)
  2. Lag + calendar  : linear regression, no census / weather
  3. Enhanced        : model 2 + weather + census (poverty, income, population)
"""
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

ROOT = Path(__file__).resolve().parents[1]
MODELS, RESULTS, SHOTS = ROOT/"ml"/"models", ROOT/"ml"/"results", ROOT/"docs"/"screenshots"
for p in (MODELS, RESULTS, SHOTS):
    p.mkdir(parents=True, exist_ok=True)

d = pd.read_parquet(ROOT/"data"/"processed"/"area_day.parquet")
d["date"] = pd.to_datetime(d["date"])
train, test = d[d["split"] == "train"].copy(), d[d["split"] == "test"].copy()
print(f"Train: {len(train):,} rows ({train.date.min().date()} to {train.date.max().date()})")
print(f"Test : {len(test):,} rows ({test.date.min().date()} to {test.date.max().date()})")
TARGET = "crime_count"

# ---- feature groups (Master Plan, 8.2)
HISTORY = ["lag_1", "lag_7", "lag_30", "rolling_7", "rolling_30"]
CAL_CAT = ["day_of_week", "month"]                 # one-hot encoded
CAL_BIN = ["is_weekend", "is_holiday"]
WEATHER = ["temperature", "rainfall"]
CENSUS = ["poverty_rate", "per_capita_income", "population"]

# ---- multicollinearity check on the census trio (+ VIF for every enhanced feature)
corr = train[CENSUS].corr()
print("\nCensus feature correlations (train):\n", corr.round(2).to_string())
dropped = []
if abs(corr.loc["poverty_rate", "per_capita_income"]) > 0.8:
    dropped.append("per_capita_income")            # plan: drop one if highly correlated
    print("\n|corr(poverty_rate, per_capita_income)| > 0.8 -> dropping per_capita_income")
census_used = [c for c in CENSUS if c not in dropped]

def vif_table(frame):
    out = []
    for c in frame.columns:
        others = frame.drop(columns=c)
        r2 = LinearRegression().fit(others, frame[c]).score(others, frame[c])
        out.append({"feature": c, "vif": np.inf if r2 >= 1 else 1 / (1 - r2)})
    return pd.DataFrame(out).sort_values("vif", ascending=False)

num_for_vif = HISTORY + CAL_BIN + WEATHER + census_used
vif = vif_table(train[num_for_vif].astype(float))
vif.to_csv(RESULTS/"regression_vif.csv", index=False)
print("\nVIF (numeric features, train) - lag/rolling overlap is expected:\n", vif.round(2).to_string(index=False))

def make_pipeline(numeric, binary):
    pre = ColumnTransformer([
        ("cat", OneHotEncoder(handle_unknown="ignore", drop="first"), CAL_CAT),
        ("num", StandardScaler(), numeric),
        ("bin", "passthrough", binary),
    ])
    return Pipeline([("prep", pre), ("lr", LinearRegression())])

FEATS_BASE = HISTORY + CAL_CAT + CAL_BIN
FEATS_ENH = FEATS_BASE + WEATHER + census_used
pipe_base = make_pipeline(HISTORY, CAL_BIN)
pipe_enh = make_pipeline(HISTORY + WEATHER + census_used, CAL_BIN)
pipe_base.fit(train[FEATS_BASE], train[TARGET])
pipe_enh.fit(train[FEATS_ENH], train[TARGET])

def metrics(name, y, p):
    return {"model": name, "MAE": mean_absolute_error(y, p),
            "RMSE": float(np.sqrt(mean_squared_error(y, p))), "R2": r2_score(y, p)}

y = test[TARGET]
pred_naive = test["lag_7"].to_numpy(float)
pred_base = np.clip(pipe_base.predict(test[FEATS_BASE]), 0, None)
pred_enh = np.clip(pipe_enh.predict(test[FEATS_ENH]), 0, None)
res = pd.DataFrame([
    metrics("Naive: same as last week (lag_7)", y, pred_naive),
    metrics("Linear regression: lag + calendar", y, pred_base),
    metrics("Linear regression: + census + weather", y, pred_enh),
])
res.to_csv(RESULTS/"regression_metrics.csv", index=False)
print("\nTEST-SET RESULTS (2025 onwards)\n", res.round(4).to_string(index=False))
gain = res.loc[1, "MAE"] - res.loc[2, "MAE"]
print(f"\nMAE change from adding census + weather: {gain:+.4f} "
      f"({gain / res.loc[1, 'MAE'] * 100:+.2f}% vs lag+calendar model)")
print("Positive = enhanced model better. Report honestly either way.")

# ---- coefficients of enhanced model
names = pipe_enh.named_steps["prep"].get_feature_names_out()
coef = pd.DataFrame({"feature": names, "coefficient": pipe_enh.named_steps["lr"].coef_})
coef = coef.reindex(coef.coefficient.abs().sort_values(ascending=False).index)
coef.to_csv(RESULTS/"regression_coefficients.csv", index=False)
print("\nLargest coefficients (enhanced model; numeric features are standardised):\n",
      coef.head(10).round(4).to_string(index=False))

# ---- predictions + plot
out = test[["community_area", "date", TARGET]].copy()
out["pred_naive_lag7"], out["pred_base"], out["pred_enhanced"] = pred_naive, pred_base, pred_enh
out.to_csv(RESULTS/"regression_test_predictions.csv", index=False)
daily = out.groupby("date")[[TARGET, "pred_naive_lag7", "pred_enhanced"]].sum()
fig, ax = plt.subplots(figsize=(11, 4.5))
ax.plot(daily.index, daily[TARGET], label="Actual", color="black", lw=1)
ax.plot(daily.index, daily["pred_enhanced"], label="Enhanced regression", color="#c0392b", lw=1)
ax.plot(daily.index, daily["pred_naive_lag7"], label="Naive (last week)", color="#2c7fb8", lw=0.8, alpha=.6)
ax.set_title("Test period: citywide daily crimes - actual vs predicted (sum of 77 areas)")
ax.set_xlabel("Date"); ax.set_ylabel("Crimes per day"); ax.legend()
plt.tight_layout(); plt.savefig(SHOTS/"12_regression_actual_vs_predicted.png", dpi=110); plt.close()

# ---- save (pipelines include encoder + scaler; feature lists keep the API input order)
joblib.dump({"baseline": pipe_base, "enhanced": pipe_enh,
             "features_baseline": FEATS_BASE, "features_enhanced": FEATS_ENH,
             "dropped_for_collinearity": dropped, "metrics": res.to_dict("records"),
             "train_end": str(train.date.max().date()), "test_start": str(test.date.min().date())},
            MODELS/"regression.pkl")
print("\nSaved ml/models/regression.pkl and results files.")