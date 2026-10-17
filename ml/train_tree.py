
"""
Phase 8.3 - Decision Tree Classification
Classifies an incident as violent (1) or non-violent (0).

Run from project root:
    python ml/train_tree.py

Input:
    data/processed/incidents.parquet

Split:
    Train: 2023-2024
    Test : 2025 onwards

Master Plan features:
    hour, day_of_week, season, location_group, domestic,
    community_area, district

Excluded:
    primary_type, crime_group, iucr, fbi_code, description,
    month, year, date, split

Outputs:
    ml/models/tree.pkl
    ml/results/tree_metrics.csv
    ml/results/tree_confusion_matrix.csv
    ml/results/tree_feature_importance.csv
    ml/results/tree_predictions.csv
    docs/screenshots/13_tree_confusion_matrix.png
    docs/screenshots/14_tree_visualization.png
    docs/screenshots/15_tree_feature_importance.png
"""

from pathlib import Path

import joblib
import numpy as np
import pandas as pd

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    ConfusionMatrixDisplay,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.tree import DecisionTreeClassifier, plot_tree


# --------------------------------------------------
# 1. Paths and configuration
# --------------------------------------------------

ROOT = Path(__file__).resolve().parents[1]

DATA_PATH = ROOT / "data" / "processed" / "incidents.parquet"
MODELS = ROOT / "ml" / "models"
RESULTS = ROOT / "ml" / "results"
SHOTS = ROOT / "docs" / "screenshots"

for folder in (MODELS, RESULTS, SHOTS):
    folder.mkdir(parents=True, exist_ok=True)

MODEL_PATH = MODELS / "tree.pkl"

SEED = 42
MAX_DEPTH = 6
MIN_SAMPLES_LEAF = 500

TARGET = "is_violent"

NUMERIC_FEATURES = ["hour", "domestic"]

CATEGORICAL_FEATURES = [
    "day_of_week",
    "season",
    "location_group",
    "community_area",
    "district",
]

FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES

REQUIRED_COLUMNS = FEATURES + [TARGET, "split", "date"]

EXCLUDED_FEATURES = [
    "primary_type",
    "crime_group",
    "iucr",
    "fbi_code",
    "description",
    "month",
    "year",
    "date",
    "split",
]


# --------------------------------------------------
# 2. Load and validate data
# --------------------------------------------------

if not DATA_PATH.exists():
    raise FileNotFoundError(
        f"Dataset not found: {DATA_PATH}\n"
        "Run the Phase 7 table-preparation step first."
    )

df = pd.read_parquet(DATA_PATH)

missing_columns = sorted(set(REQUIRED_COLUMNS) - set(df.columns))
if missing_columns:
    raise ValueError(f"Missing required columns: {missing_columns}")

df = df.copy()
df["date"] = pd.to_datetime(df["date"], errors="raise")

if df[TARGET].isna().any():
    raise ValueError("Target is_violent contains missing values.")

target_values = set(df[TARGET].unique())
if not target_values.issubset({0, 1}):
    raise ValueError(
        f"Expected binary target labels 0 and 1; got {target_values}"
    )

if df[FEATURES].isna().any().any():
    missing_counts = df[FEATURES].isna().sum()
    missing_counts = missing_counts[missing_counts > 0]
    raise ValueError(
        "Missing values found in model features:\n"
        f"{missing_counts.to_string()}"
    )

if not df["split"].isin(["train", "test"]).all():
    raise ValueError("Unexpected values found in split column.")

train = df.loc[df["split"] == "train"].copy()
test = df.loc[df["split"] == "test"].copy()

if train.empty or test.empty:
    raise ValueError("Training or test split is empty.")

train_max_date = train["date"].max()
test_min_date = test["date"].min()

if train_max_date >= test_min_date:
    raise ValueError(
        "Chronological split validation failed: "
        f"latest train date={train_max_date.date()}, "
        f"earliest test date={test_min_date.date()}."
    )

print("=" * 65)
print("PHASE 8.3 - DECISION TREE CLASSIFICATION")
print("=" * 65)
print(f"Dataset rows       : {len(df):,}")
print(f"Training rows      : {len(train):,}")
print(f"Test rows          : {len(test):,}")
print(f"Train date range   : {train['date'].min().date()} to "
      f"{train_max_date.date()}")
print(f"Test date range    : {test_min_date.date()} to "
      f"{test['date'].max().date()}")
print(f"Violent share train: {train[TARGET].mean() * 100:.2f}%")
print(f"Violent share test : {test[TARGET].mean() * 100:.2f}%")
print(f"Features           : {FEATURES}")
print("Leakage columns    : excluded")


# --------------------------------------------------
# 3. Prepare features and target
# --------------------------------------------------

X_train = train[FEATURES]
y_train = train[TARGET].astype(int)

X_test = test[FEATURES]
y_test = test[TARGET].astype(int)


# --------------------------------------------------
# 4. Build the model pipeline
# --------------------------------------------------

def make_pipeline(class_weight=None):
    """
    One-hot encode categorical features and pass numeric
    features through unchanged, then fit a decision tree.
    """

    preprocessing = ColumnTransformer(
        transformers=[
            (
                "cat",
                OneHotEncoder(
                    handle_unknown="ignore",
                    dtype=np.float32,
                ),
                CATEGORICAL_FEATURES,
            ),
            ("num", "passthrough", NUMERIC_FEATURES),
        ],
        remainder="drop",
    )

    classifier = DecisionTreeClassifier(
        max_depth=MAX_DEPTH,
        min_samples_leaf=MIN_SAMPLES_LEAF,
        class_weight=class_weight,
        random_state=SEED,
    )

    return Pipeline([
        ("prep", preprocessing),
        ("tree", classifier),
    ])


# --------------------------------------------------
# 5. Train baseline, main tree and balanced comparison
# --------------------------------------------------

print("\nTraining models...")

# Baseline predicts the most frequent training class.
baseline = DummyClassifier(strategy="most_frequent")
baseline.fit(X_train, y_train)

# Main model: this is the model saved for later use.
tree_model = make_pipeline(class_weight=None)
tree_model.fit(X_train, y_train)

# Comparison model: gives additional weight to the minority class.
balanced_model = make_pipeline(class_weight="balanced")
balanced_model.fit(X_train, y_train)

baseline_pred = baseline.predict(X_test)
tree_pred = tree_model.predict(X_test)
balanced_pred = balanced_model.predict(X_test)

# Probability of the positive class (violent = 1).
tree_classes = list(tree_model.named_steps["tree"].classes_)
violent_index = tree_classes.index(1)
violent_probability = tree_model.predict_proba(X_test)[:, violent_index]


# --------------------------------------------------
# 6. Evaluate all models on the same test set
# --------------------------------------------------

def calculate_metrics(model_name, y_true, predictions):
    """Return metrics for the violent class and overall accuracy."""

    return {
        "model": model_name,
        "accuracy": accuracy_score(y_true, predictions),
        "balanced_accuracy": balanced_accuracy_score(
            y_true, predictions
        ),
        "precision_violent": precision_score(
            y_true, predictions, zero_division=0
        ),
        "recall_violent": recall_score(
            y_true, predictions, zero_division=0
        ),
        "f1_violent": f1_score(
            y_true, predictions, zero_division=0
        ),
    }


metrics = pd.DataFrame([
    calculate_metrics(
        "Baseline: majority class",
        y_test,
        baseline_pred,
    ),
    calculate_metrics(
        f"Decision Tree (depth={MAX_DEPTH}, leaf={MIN_SAMPLES_LEAF})",
        y_test,
        tree_pred,
    ),
    calculate_metrics(
        f"Balanced Tree (depth={MAX_DEPTH}, leaf={MIN_SAMPLES_LEAF})",
        y_test,
        balanced_pred,
    ),
])

metrics.to_csv(RESULTS / "tree_metrics.csv", index=False)

print("\nTEST-SET METRICS (2025 onwards)")
print(metrics.round(4).to_string(index=False))

print("\nClassification report - main tree:")
print(
    classification_report(
        y_test,
        tree_pred,
        labels=[0, 1],
        target_names=["non-violent", "violent"],
        digits=4,
        zero_division=0,
    )
)


# --------------------------------------------------
# 7. Confusion matrix for the main model
# --------------------------------------------------

cm = confusion_matrix(y_test, tree_pred, labels=[0, 1])

cm_df = pd.DataFrame(
    cm,
    index=["actual_non_violent", "actual_violent"],
    columns=["pred_non_violent", "pred_violent"],
)
cm_df.to_csv(RESULTS / "tree_confusion_matrix.csv")

print("Confusion matrix (rows = actual, columns = predicted):")
print(cm_df)

fig, ax = plt.subplots(figsize=(7, 5))

ConfusionMatrixDisplay(
    confusion_matrix=cm,
    display_labels=["Non-violent", "Violent"],
).plot(
    ax=ax,
    cmap="Blues",
    values_format="d",
    colorbar=False,
)

ax.set_title("Decision Tree - Confusion Matrix (Test Set)")
plt.tight_layout()
plt.savefig(
    SHOTS / "13_tree_confusion_matrix.png",
    dpi=150,
    bbox_inches="tight",
)
plt.close(fig)


# --------------------------------------------------
# 8. Feature importance
# --------------------------------------------------

preprocessor = tree_model.named_steps["prep"]
classifier = tree_model.named_steps["tree"]

encoded_names = preprocessor.get_feature_names_out()
encoded_importances = classifier.feature_importances_

if len(encoded_names) != len(encoded_importances):
    raise RuntimeError(
        "Feature-name and feature-importance lengths do not match."
    )

importance_df = pd.DataFrame({
    "encoded_feature": encoded_names,
    "importance": encoded_importances,
})


def original_feature_name(encoded_name):
    """
    Map an encoded feature back to its original input column.
    Example: cat__season_Winter -> season
    """

    transformer, feature_name = encoded_name.split("__", 1)

    if transformer == "num":
        return feature_name

    # Match the original categorical column prefix.
    for column in sorted(CATEGORICAL_FEATURES, key=len, reverse=True):
        if feature_name == column or feature_name.startswith(column + "_"):
            return column

    raise ValueError(
        f"Could not map encoded feature to source column: {encoded_name}"
    )


importance_df["original_feature"] = importance_df[
    "encoded_feature"
].map(original_feature_name)

importance_df = importance_df.sort_values(
    "importance", ascending=False
).reset_index(drop=True)

importance_df.to_csv(
    RESULTS / "tree_feature_importance.csv",
    index=False,
)

# Sum the importance of all one-hot columns belonging to a source feature.
grouped_importance = (
    importance_df.groupby("original_feature")["importance"]
    .sum()
    .sort_values(ascending=True)
)

print("\nImportance by original feature:")
print(grouped_importance.sort_values(ascending=False).round(4).to_string())

fig, ax = plt.subplots(figsize=(9, 5))

grouped_importance.plot(kind="barh", ax=ax)
ax.set_title("Decision Tree - Feature Importance")
ax.set_xlabel("Importance")
ax.set_ylabel("Original feature")

plt.tight_layout()
plt.savefig(
    SHOTS / "15_tree_feature_importance.png",
    dpi=150,
    bbox_inches="tight",
)
plt.close(fig)


# --------------------------------------------------
# 9. Visualize the upper levels of the trained tree
# --------------------------------------------------

# The full model has depth up to 6. Display only the top 3 levels
# so the figure remains readable.
fig, ax = plt.subplots(figsize=(24, 11))

plot_tree(
    classifier,
    feature_names=list(encoded_names),
    class_names=["non-violent", "violent"],
    max_depth=3,
    filled=True,
    rounded=True,
    fontsize=8,
    ax=ax,
)

ax.set_title(
    f"Decision Tree - Top 3 Levels "
    f"(maximum model depth = {MAX_DEPTH})"
)

plt.tight_layout()
plt.savefig(
    SHOTS / "14_tree_visualization.png",
    dpi=130,
    bbox_inches="tight",
)
plt.close(fig)


# --------------------------------------------------
# 10. Save test-set predictions
# --------------------------------------------------

predictions_df = pd.DataFrame({
    "date": test["date"].to_numpy(),
    "actual": y_test.to_numpy(),
    "predicted": tree_pred,
    "prob_violent": violent_probability,
})

predictions_df.to_csv(
    RESULTS / "tree_predictions.csv",
    index=False,
)


# --------------------------------------------------
# 11. Save the trained model and metadata
# --------------------------------------------------

artifact = {
    "pipeline": tree_model,
    "features": FEATURES,
    "numeric_features": NUMERIC_FEATURES,
    "categorical_features": CATEGORICAL_FEATURES,
    "target": TARGET,
    "max_depth": MAX_DEPTH,
    "min_samples_leaf": MIN_SAMPLES_LEAF,
    "class_weight": None,
    "classes": {
        0: "non-violent",
        1: "violent",
    },
    "train_date_range": (
        str(train["date"].min().date()),
        str(train["date"].max().date()),
    ),
    "test_date_range": (
        str(test["date"].min().date()),
        str(test["date"].max().date()),
    ),
    "excluded_features": EXCLUDED_FEATURES,
    "metrics": metrics.to_dict(orient="records"),
}

joblib.dump(artifact, MODEL_PATH)


# --------------------------------------------------
# 12. Final verification
# --------------------------------------------------

output_files = [
    MODEL_PATH,
    RESULTS / "tree_metrics.csv",
    RESULTS / "tree_confusion_matrix.csv",
    RESULTS / "tree_feature_importance.csv",
    RESULTS / "tree_predictions.csv",
    SHOTS / "13_tree_confusion_matrix.png",
    SHOTS / "14_tree_visualization.png",
    SHOTS / "15_tree_feature_importance.png",
]

print("\nOUTPUT VERIFICATION")
for path in output_files:
    print(f"{'OK' if path.exists() else 'MISSING'}: {path.relative_to(ROOT)}")

print("\nPhase 8.3 completed successfully.")
print("Main saved model: ml/models/tree.pkl")
