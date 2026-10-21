import json
from datetime import timedelta
from pathlib import Path

import holidays
import joblib
import numpy as np
import pandas as pd
from sqlalchemy import text

from .db import engine

ROOT = Path(__file__).resolve().parents[2]          # project root
MODELS = ROOT / "ml" / "models"
ASSETS = ROOT / "ml" / "results" / "api_assets"
CENSUS_COLS = ["poverty_rate", "per_capita_income", "population"]
RULE_FIELDS = {"district", "location_group", "time_of_day", "is_weekend", "season"}
RULE_OUTCOMES = {"THEFT", "BATTERY", "ALL OTHER"}


class ModelStore:
    """Holds every model and lookup table. Loaded once, when the API starts."""

    def __init__(self):
        self.kmeans = None
        self.clusters = None
        self.area_points = {}          # community_area -> (lat, lon, name)
        self.regression = None
        self.census = None             # indexed by community_area
        self.month_weather = {}        # month -> (avg_temperature, avg_rainfall)
        self.il_holidays = None
        self.data_as_of = None         # last date with crime data (Timestamp)
        self.tree = None
        self.rules = None              # list of dicts, sorted by lift (high to low)

    def load(self):
        self.kmeans = joblib.load(MODELS / "kmeans.pkl")
        self.clusters = pd.read_csv(ASSETS / "hotspot_clusters.csv")
        self._check_kmeans()
        self._load_area_points()
        print(f"Loaded K-Means: k={self.kmeans['k']}, "
              f"{len(self.clusters)} cluster rows, {len(self.area_points)} area locations")
        self._load_regression()
        self._load_tree()
        self._load_rules()

    # ---------------- K-Means ----------------
    def to_km(self, lat: float, lon: float) -> np.ndarray:
        """Same projection as ml/train_kmeans.py: x = longitude, y = latitude, in km."""
        x = lon * float(self.kmeans["km_per_deg_lon"])
        y = lat * float(self.kmeans["km_per_deg_lat"])
        return np.array([[x, y]])

    def predict_cluster(self, lat: float, lon: float) -> int:
        return int(self.kmeans["model"].predict(self.to_km(lat, lon))[0])

    def _check_kmeans(self):
        """Each saved cluster centre must map back to its own cluster."""
        for r in self.clusters.itertuples():
            got = self.predict_cluster(r.centre_lat, r.centre_lon)
            if got != int(r.cluster):
                raise RuntimeError(
                    f"K-Means self-check failed: centre of cluster {r.cluster} "
                    f"was assigned to cluster {got}. Check the km projection.")
        print("K-Means self-check passed")

    def _load_area_points(self):
        sql = ("SELECT l.community_area, MAX(l.area_name) AS area_name, "
               "AVG(f.latitude) AS lat, AVG(f.longitude) AS lon "
               "FROM fact_crime f JOIN dim_location l ON l.location_key = f.location_key "
               "WHERE f.latitude IS NOT NULL GROUP BY l.community_area")
        try:
            with engine.connect() as conn:
                rows = conn.execute(text(sql)).all()
            self.area_points = {int(r.community_area): (float(r.lat), float(r.lon), r.area_name)
                                for r in rows}
        except Exception as exc:       # the API still starts without the database
            print("WARNING: could not load area locations:", exc)

    # ---------------- Regression (forecast) ----------------
    def _load_regression(self):
        self.regression = joblib.load(MODELS / "regression.pkl")

        census = pd.read_csv(ASSETS / "area_census.csv")
        missing = [c for c in CENSUS_COLS if c not in census.columns]
        if missing:
            raise RuntimeError(f"area_census.csv is missing columns: {missing}")
        self.census = census.set_index("community_area")

        weather = pd.read_csv(ASSETS / "historical_monthly_weather.csv")
        self.month_weather = {int(r.month): (float(r.avg_temperature), float(r.avg_rainfall))
                              for r in weather.itertuples()}

        self.il_holidays = holidays.country_holidays("US", subdiv="IL", years=range(2023, 2028))

        self.data_as_of = self._find_data_as_of()
        print(f"Loaded regression: {len(self.regression['features_enhanced'])} features, "
              f"data as of {self.data_as_of.date()}")

    def _find_data_as_of(self) -> pd.Timestamp:
        try:
            with engine.connect() as conn:
                last = conn.execute(text("SELECT MAX(full_date) FROM dim_date")).scalar()
            return pd.Timestamp(last)
        except Exception as exc:       # fall back to the exported manifest
            print("WARNING: could not read the last date from the database:", exc)
            manifest = json.loads((ASSETS / "manifest.json").read_text())
            return pd.Timestamp(manifest["latest_crime_data_date"])

    def history(self, area: int, days: int = 45, end=None) -> pd.Series:
        """Daily crime counts for one area, ending on `end` (default: data_as_of).
        Zero-crime days are included."""
        end = self.data_as_of if end is None else pd.Timestamp(end)
        start = end - timedelta(days=days - 1)
        sql = text("SELECT d.full_date AS day, COUNT(*) AS n "
                   "FROM fact_crime f "
                   "JOIN dim_date d ON d.date_key = f.date_key "
                   "JOIN dim_location l ON l.location_key = f.location_key "
                   "WHERE l.community_area = :area "
                   "AND d.full_date BETWEEN :start AND :end "
                   "GROUP BY d.full_date")
        with engine.connect() as conn:
            rows = conn.execute(sql, {"area": area, "start": start.date(),
                                      "end": end.date()}).all()
        counts = pd.Series({pd.Timestamp(r.day): int(r.n) for r in rows}, dtype="int64")
        full_range = pd.date_range(start, end, freq="D")
        return counts.reindex(full_range, fill_value=0)

    def build_row(self, area: int, day, hist: pd.Series,
                  temperature=None, rainfall=None) -> pd.DataFrame:
        """One row of model features for `day`, built only from counts BEFORE `day`.
        Same definitions as ml/prepare_tables.py: lag_k = count k days ago,
        rolling_30 = mean of the 30 days ending yesterday."""
        d = pd.Timestamp(day)
        one = pd.Timedelta(days=1)
        avg_temp, avg_rain = self.month_weather[d.month]
        census = self.census.loc[area]
        row = {
            "lag_1": float(hist.loc[d - one]),
            "lag_7": float(hist.loc[d - 7 * one]),
            "lag_30": float(hist.loc[d - 30 * one]),
            "rolling_30": float(hist.loc[d - 30 * one: d - one].mean()),
            "day_of_week": int(d.dayofweek),
            "month": int(d.month),
            "is_weekend": int(d.dayofweek >= 5),
            "is_holiday": int(d.date() in self.il_holidays),
            "temperature": avg_temp if temperature is None else float(temperature),
            "rainfall": avg_rain if rainfall is None else float(rainfall),
            "poverty_rate": float(census["poverty_rate"]),
            "per_capita_income": float(census["per_capita_income"]),
            "population": float(census["population"]),
        }
        return pd.DataFrame([row])[self.regression["features_enhanced"]]

    def forecast(self, area: int, days: int = 7):
        """Predict the next `days` days after data_as_of. Each prediction is added to the
        history, so later days use earlier predictions as their lags (Master Plan, Phase 10)."""
        actual = self.history(area, 45).astype(float)
        series = actual.copy()
        predictions = []
        for i in range(1, days + 1):
            day = self.data_as_of + timedelta(days=i)
            x = self.build_row(area, day, series)
            yhat = max(0.0, float(self.regression["enhanced"].predict(x)[0]))
            predictions.append((day, yhat))
            series.loc[day] = yhat
        return actual, predictions

    # ---------------- Decision Tree (violence risk) ----------------
    def _load_tree(self):
        self.tree = joblib.load(MODELS / "tree.pkl")
        probe = self.violence_row(hour=12, domestic=0, day_of_week=2, season="SUMMER",
                                  location_group="STREET", community_area=25, district=15)
        pipe = self.tree["pipeline"]
        proba = pipe.predict_proba(probe)[0]
        if sorted(list(pipe.classes_)) != [0, 1] or abs(float(proba.sum()) - 1.0) > 1e-6:
            raise RuntimeError("Decision Tree self-check failed: unexpected classes "
                               f"{list(pipe.classes_)} or probabilities {proba}")
        print(f"Loaded decision tree: {len(self.tree['features'])} features, self-check passed")

    def violence_row(self, hour, domestic, day_of_week, season, location_group,
                     community_area, district) -> pd.DataFrame:
        """One row with the tree's features, in the order it was trained on."""
        row = {"hour": int(hour), "domestic": int(domestic), "day_of_week": int(day_of_week),
               "season": str(season), "location_group": str(location_group),
               "community_area": int(community_area), "district": int(district)}
        return pd.DataFrame([row])[list(self.tree["features"])]

    def predict_violence(self, **inputs) -> float:
        """Probability (0 to 1) that an incident with these features is violent."""
        pipe = self.tree["pipeline"]
        proba = pipe.predict_proba(self.violence_row(**inputs))[0]
        return float(proba[list(pipe.classes_).index(1)])

    # ---------------- Association rules (patterns) ----------------
    def _load_rules(self):
        df = pd.read_csv(MODELS / "rules.csv")
        needed = {"antecedent_str", "consequent_str", "support", "confidence", "lift"}
        if not needed <= set(df.columns):
            raise RuntimeError(f"rules.csv is missing columns: {sorted(needed - set(df.columns))}")
        rules = []
        for r in df.itertuples():
            conditions = {}
            for part in str(r.antecedent_str).split(" AND "):
                key, _, value = part.partition("=")
                if key not in RULE_FIELDS or not value:
                    raise RuntimeError(f"Unexpected condition '{part}' in rules.csv")
                conditions[key] = value
            key, _, outcome = str(r.consequent_str).partition("=")
            if key != "crime_group" or outcome not in RULE_OUTCOMES:
                raise RuntimeError(f"Unexpected outcome '{r.consequent_str}' in rules.csv")
            rules.append({"conditions": conditions, "outcome": outcome,
                          "support": float(r.support), "confidence": float(r.confidence),
                          "lift": float(r.lift)})
        self.rules = sorted(rules, key=lambda x: x["lift"], reverse=True)
        districts = sorted({v for r in rules for k, v in r["conditions"].items() if k == "district"})
        print(f"Loaded association rules: {len(self.rules)} rules, districts with rules: {districts}")

    def match_rules(self, chosen: dict, outcome=None) -> list:
        """Rules whose conditions are ALL among the chosen ones (best lift first).
        With nothing chosen, every rule is returned."""
        items = set(chosen.items())
        found = []
        for r in self.rules:
            if chosen and not set(r["conditions"].items()) <= items:
                continue
            if outcome is not None and r["outcome"] != outcome:
                continue
            found.append(r)
        return found

    def loaded(self) -> list[str]:
        names = {"kmeans": self.kmeans, "regression": self.regression, "tree": self.tree,
                 "rules": self.rules}
        return [name for name, obj in names.items() if obj is not None]


store = ModelStore()