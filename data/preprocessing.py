
"""Preprocess the official Amazon ESCI dataset for RankEngine."""

from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.dataset as ds


PROJECT_ROOT = Path(__file__).resolve().parents[1]

RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

EXAMPLES_FILE = RAW_DIR / "shopping_queries_dataset_examples.parquet"
PRODUCTS_FILE = RAW_DIR / "shopping_queries_dataset_products.parquet"

LABEL_MAP = {
    "E": 3,  # Exact
    "S": 2,  # Substitute
    "C": 1,  # Complement
    "I": 0,  # Irrelevant
}

JOIN_KEYS = ["product_id", "product_locale"]

PRODUCT_COLUMNS = [
    "product_id",
    "product_locale",
    "product_title",
    "product_description",
    "product_bullet_point",
    "product_brand",
    "product_color",
]

TEXT_COLUMNS = [
    "query",
    "product_title",
    "product_description",
    "product_bullet_point",
    "product_brand",
    "product_color",
]


def clean_text(series: pd.Series) -> pd.Series:
    """Replace missing text with empty strings and normalize whitespace."""
    return (
        series.fillna("")
        .astype(str)
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
    )


def preprocess_dataset() -> None:
    """Create clean train and test Parquet files for ESCI Task 1."""

    if not EXAMPLES_FILE.exists():
        raise FileNotFoundError(f"Examples dataset not found: {EXAMPLES_FILE}")

    if not PRODUCTS_FILE.exists():
        raise FileNotFoundError(f"Products dataset not found: {PRODUCTS_FILE}")

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    print("1/6 Loading example judgments...")

    examples = pd.read_parquet(
        EXAMPLES_FILE,
        columns=[
            "example_id",
            "query",
            "query_id",
            "product_id",
            "product_locale",
            "esci_label",
            "small_version",
            "split",
        ],
    )

    # Use the official reduced Task 1 subset.
    examples = examples.loc[examples["small_version"] == 1].copy()

    print(f"Task 1 judgments: {len(examples):,}")

    # Validate the official relevance labels.
    unexpected_labels = set(examples["esci_label"].dropna().unique()) - set(
        LABEL_MAP
    )
    if unexpected_labels:
        raise ValueError(f"Unexpected ESCI labels: {unexpected_labels}")

    if examples["esci_label"].isna().any():
        raise ValueError("Some Task 1 examples have missing relevance labels.")

    # Keep only rows belonging to the official train/test split.
    invalid_splits = set(examples["split"].dropna().unique()) - {
        "train",
        "test",
    }
    if invalid_splits or examples["split"].isna().any():
        raise ValueError(f"Unexpected or missing split values: {invalid_splits}")

    print("2/6 Selecting matching product records...")

    product_ids = examples["product_id"].dropna().unique()

    # Filter the Parquet dataset before converting product text to pandas.
    product_dataset = ds.dataset(str(PRODUCTS_FILE), format="parquet")

    product_filter = ds.field("product_id").isin(product_ids.tolist())

    product_table = product_dataset.to_table(
        columns=PRODUCT_COLUMNS,
        filter=product_filter,
    )

    products = product_table.to_pandas()
    del product_table

    print(f"Matching product records loaded: {len(products):,}")

    print("3/6 Checking product keys...")

    if products[JOIN_KEYS].isna().any().any():
        raise ValueError("Product data contains missing join keys.")

    duplicate_products = products.duplicated(JOIN_KEYS, keep=False)

    if duplicate_products.any():
        duplicate_count = int(duplicate_products.sum())
        raise ValueError(
            f"Found {duplicate_count:,} product rows with duplicate "
            f"(product_id, product_locale) keys. Resolve this before "
            f"joining; the script will not silently discard product records."
        )

    print("Product join keys are unique.")

    print("4/6 Joining judgments with product details...")

    merged = examples.merge(
        products,
        on=JOIN_KEYS,
        how="left",
        validate="many_to_one",
        indicator=True,
    )

    unmatched_count = int((merged["_merge"] == "left_only").sum())

    print(f"Examples without a matching product: {unmatched_count:,}")

    # Retain only judgments for which product details are available.
    merged = merged.loc[merged["_merge"] == "both"].copy()
    merged.drop(columns=["_merge", "small_version"], inplace=True)

    if merged.empty:
        raise ValueError("The join produced no matched examples.")

    print("5/6 Cleaning text and creating relevance scores...")

    for column in TEXT_COLUMNS:
        merged[column] = clean_text(merged[column])

    merged["relevance"] = (
        merged["esci_label"].map(LABEL_MAP).astype("int8")
    )

    # Put important identifiers and ranking fields first.
    output_columns = [
        "example_id",
        "query_id",
        "query",
        "product_id",
        "product_locale",
        "product_title",
        "product_description",
        "product_bullet_point",
        "product_brand",
        "product_color",
        "esci_label",
        "relevance",
        "split",
    ]

    merged = merged[output_columns]

    train = merged.loc[merged["split"] == "train"].copy()
    test = merged.loc[merged["split"] == "test"].copy()

    train_path = PROCESSED_DIR / "task1_train.parquet"
    test_path = PROCESSED_DIR / "task1_test.parquet"

    train.to_parquet(train_path, index=False, compression="snappy")
    test.to_parquet(test_path, index=False, compression="snappy")

    print("6/6 Preprocessing completed.")
    print(f"Matched examples: {len(merged):,}")
    print(f"Training rows:    {len(train):,}")
    print(f"Testing rows:     {len(test):,}")
    print(f"Training file:    {train_path}")
    print(f"Testing file:     {test_path}")
    print(f"Relevance mapping: {LABEL_MAP}")


if __name__ == "__main__":
    preprocess_dataset()
