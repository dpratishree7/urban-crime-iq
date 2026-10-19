
"""
Phase 8.4 - Apriori Association Rule Mining

Purpose:
    Discover descriptive association patterns in crime data.
    These patterns are NOT predictions and do NOT imply causation.

Run from project root:
    python ml/train_apriori.py

Input:
    data/processed/categorical.parquet

Expected categories:
    time_of_day, location_group, crime_group, season,
    is_weekend, district

Final configuration:
    min_support = 0.01
    min_confidence = 0.30
    max_len = 4

Outputs:
    ml/models/rules.csv
    ml/results/apriori_all_rules.csv
    ml/results/apriori_top10_lift.csv
    ml/results/apriori_frequent_itemsets.csv
"""

from pathlib import Path

import pandas as pd
from mlxtend.frequent_patterns import apriori, association_rules


# --------------------------------------------------
# 1. Paths and final configuration
# --------------------------------------------------

ROOT = Path(__file__).resolve().parents[1]

DATA_PATH = ROOT / "data" / "processed" / "categorical.parquet"
MODELS = ROOT / "ml" / "models"
RESULTS = ROOT / "ml" / "results"

for folder in (MODELS, RESULTS):
    folder.mkdir(parents=True, exist_ok=True)

# Final support selected after testing 0.02, 0.015 and 0.01.
# At 0.01, four positive-lift crime rules were discovered.
SEED_SUPPORTS = [0.01]

MIN_CONFIDENCE = 0.30
MAX_LEN = 4

EXPECTED_GROUPS = [
    "time_of_day",
    "location_group",
    "crime_group",
    "season",
    "is_weekend",
    "district",
]


# --------------------------------------------------
# 2. Load and validate one-hot data
# --------------------------------------------------

if not DATA_PATH.exists():
    raise FileNotFoundError(f"Dataset not found: {DATA_PATH}")

df = pd.read_parquet(DATA_PATH)

if df.empty:
    raise ValueError("categorical.parquet contains no rows.")

if df.columns.duplicated().any():
    duplicates = df.columns[df.columns.duplicated()].tolist()
    raise ValueError(f"Duplicate column names: {duplicates}")


def column_group(column):
    """Identify the category represented by a dummy column."""
    for group in sorted(EXPECTED_GROUPS, key=len, reverse=True):
        if (
            column == group
            or column.startswith(group + "=")
            or column.startswith(group + "_")
        ):
            return group
    return None


grouped_columns = {
    group: [c for c in df.columns if column_group(c) == group]
    for group in EXPECTED_GROUPS
}

missing_groups = [
    group
    for group, columns in grouped_columns.items()
    if not columns
]

if missing_groups:
    raise ValueError(
        "Could not identify columns for these expected categories: "
        f"{missing_groups}\n"
        "Inspect categorical.parquet column names and update "
        "column_group()."
    )

# Apriori requires binary transaction indicators.
for column in df.columns:
    values = set(df[column].dropna().unique())

    if not values.issubset({0, 1, False, True}):
        raise ValueError(
            f"Column {column!r} is not binary. "
            f"Values found: {list(values)[:10]}"
        )

if df.isna().any().any():
    raise ValueError(
        "Missing values found in one-hot data. "
        "Resolve them before Apriori."
    )

# Boolean columns are compatible with mlxtend.
df = df.astype(bool)

print("=" * 65)
print("PHASE 8.4 - APRIORI ASSOCIATION RULE MINING")
print("=" * 65)
print(f"Transactions: {len(df):,}")
print(f"One-hot columns: {len(df.columns)}")

for group, columns in grouped_columns.items():
    print(f"  {group}: {len(columns)} columns")

# Check one-hot consistency within each category.
# Rows with no active item are allowed, but multiple active
# categories within a group are not.
for group, columns in grouped_columns.items():
    active_counts = df[columns].sum(axis=1)
    multi_active = int((active_counts > 1).sum())

    if multi_active:
        raise ValueError(
            f"{group} has {multi_active:,} rows with multiple "
            "active categories. Check the one-hot encoding."
        )

    missing_category = int((active_counts == 0).sum())

    if missing_category:
        print(
            f"WARNING: {group} has {missing_category:,} rows "
            "with no active category."
        )


# --------------------------------------------------
# 3. Helper functions
# --------------------------------------------------

def format_itemset(items):
    """Convert a frozenset of item labels into readable text."""
    return " AND ".join(sorted(map(str, items)))


def is_crime_group_item(item):
    """Recognize supported crime_group dummy-column conventions."""
    item = str(item)
    return (
        item.startswith("crime_group=")
        or item.startswith("crime_group_")
    )


def get_association_rules(itemsets, transaction_count):
    """
    Support mlxtend versions with and without num_itemsets.
    """
    try:
        return association_rules(
            itemsets,
            metric="confidence",
            min_threshold=MIN_CONFIDENCE,
        )
    except TypeError:
        return association_rules(
            itemsets,
            num_itemsets=transaction_count,
            metric="confidence",
            min_threshold=MIN_CONFIDENCE,
        )


# --------------------------------------------------
# 4. Find frequent itemsets and association rules
# --------------------------------------------------

frequent_itemsets = pd.DataFrame()
all_rules = pd.DataFrame()
used_support = None

for support in SEED_SUPPORTS:
    print(f"\nTrying min_support={support:.4f}...")

    candidate_itemsets = apriori(
        df,
        min_support=support,
        use_colnames=True,
        max_len=MAX_LEN,
        low_memory=True,
    )

    print(f"  Frequent itemsets: {len(candidate_itemsets):,}")

    if candidate_itemsets.empty:
        continue

    candidate_rules = get_association_rules(
        candidate_itemsets,
        transaction_count=len(df),
    )

    print(
        f"  Rules with confidence >= {MIN_CONFIDENCE:.2f}: "
        f"{len(candidate_rules):,}"
    )

    if not candidate_rules.empty:
        frequent_itemsets = candidate_itemsets
        all_rules = candidate_rules
        used_support = support
        break

if used_support is None:
    raise SystemExit(
        "No association rules found at the selected support. "
        "Check the input categories and review support/confidence "
        "settings with the project team."
    )


# --------------------------------------------------
# 5. Format and save all discovered rules
# --------------------------------------------------

all_rules = all_rules.copy()

all_rules["antecedent_str"] = all_rules["antecedents"].apply(
    format_itemset
)
all_rules["consequent_str"] = all_rules["consequents"].apply(
    format_itemset
)

RULE_COLUMNS = [
    "antecedent_str",
    "consequent_str",
    "support",
    "confidence",
    "lift",
    "leverage",
    "conviction",
]

# Keep all rules meeting the confidence threshold,
# including rules whose lift is <= 1.
all_rules = all_rules.sort_values(
    ["lift", "confidence", "support"],
    ascending=[False, False, False],
)

all_rules[RULE_COLUMNS].to_csv(
    RESULTS / "apriori_all_rules.csv",
    index=False,
)

itemsets_export = frequent_itemsets.copy()
itemsets_export["itemset"] = itemsets_export["itemsets"].apply(
    format_itemset
)

itemsets_export.drop(columns=["itemsets"]).to_csv(
    RESULTS / "apriori_frequent_itemsets.csv",
    index=False,
)


# --------------------------------------------------
# 6. Select crime-pattern rules
# --------------------------------------------------

# The consequent must be exactly one crime_group category.
# The antecedent must not contain any crime_group category.
crime_rules = all_rules.loc[
    all_rules["consequents"].apply(
        lambda items: (
            len(items) == 1
            and all(is_crime_group_item(item) for item in items)
        )
    )
    & all_rules["antecedents"].apply(
        lambda items: not any(
            is_crime_group_item(item) for item in items
        )
    )
].copy()

# Lift > 1 indicates that the consequent appears more often
# with the antecedent than expected under independence.
# This does not imply causation.
positive_crime_rules = crime_rules.loc[
    crime_rules["lift"] > 1
].copy()

positive_crime_rules = positive_crime_rules.sort_values(
    ["lift", "confidence", "support"],
    ascending=[False, False, False],
)

positive_crime_rules[RULE_COLUMNS].to_csv(
    MODELS / "rules.csv",
    index=False,
)

# Keep at most ten rules. Fewer than ten is valid.
top10 = positive_crime_rules.head(10)

top10[RULE_COLUMNS].to_csv(
    RESULTS / "apriori_top10_lift.csv",
    index=False,
)


# --------------------------------------------------
# 7. Summary and output verification
# --------------------------------------------------

print("\n" + "=" * 65)
print("APRIORI SUMMARY")
print("=" * 65)
print(f"Final minimum support: {used_support}")
print(f"Minimum confidence: {MIN_CONFIDENCE}")
print(f"Maximum itemset length: {MAX_LEN}")
print(f"Frequent itemsets: {len(frequent_itemsets):,}")
print(f"All discovered rules: {len(all_rules):,}")
print(f"Crime-consequent rules: {len(crime_rules):,}")
print(f"Positive-lift crime rules: {len(positive_crime_rules):,}")

pd.set_option("display.width", 220)
pd.set_option("display.max_colwidth", 90)

if top10.empty:
    print(
        "\nNo crime-pattern rules with lift > 1 were found. "
        "Review the full rule output and support settings."
    )
else:
    print("\nTOP CRIME-PATTERN RULES BY LIFT")
    print(top10[RULE_COLUMNS].round(4).to_string(index=False))

output_files = [
    MODELS / "rules.csv",
    RESULTS / "apriori_all_rules.csv",
    RESULTS / "apriori_top10_lift.csv",
    RESULTS / "apriori_frequent_itemsets.csv",
]

print("\nOUTPUT VERIFICATION")
for path in output_files:
    print(
        f"{'OK' if path.exists() else 'MISSING'}: "
        f"{path.relative_to(ROOT)}"
    )

missing_outputs = [path for path in output_files if not path.exists()]
if missing_outputs:
    raise RuntimeError(f"Missing output files: {missing_outputs}")

print("\nPhase 8.4 completed successfully.")
print("Association rules are descriptive, not causal.")
