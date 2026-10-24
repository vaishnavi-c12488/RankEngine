
"""Inspect raw ESCI catalog coverage without modifying project data."""

from pathlib import Path

import pyarrow.dataset as ds


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"

EXAMPLES_FILE = RAW_DIR / "shopping_queries_dataset_examples.parquet"
PRODUCTS_FILE = RAW_DIR / "shopping_queries_dataset_products.parquet"


def main() -> None:
    for path in (EXAMPLES_FILE, PRODUCTS_FILE):
        if not path.exists():
            raise FileNotFoundError(f"Dataset not found: {path}")

    examples = ds.dataset(str(EXAMPLES_FILE), format="parquet")
    products = ds.dataset(str(PRODUCTS_FILE), format="parquet")

    print("Raw example columns:", examples.schema.names)
    print("Raw product columns:", products.schema.names)

    example_table = examples.to_table(
        columns=["product_id", "product_locale", "small_version", "split"]
    )
    example_df = example_table.to_pandas()
    task1 = example_df.loc[example_df["small_version"] == 1]

    print("\nTask 1 unique judged product/locale pairs:")
    print(
        task1[["product_id", "product_locale"]]
        .drop_duplicates()
        .groupby("product_locale")
        .size()
        .to_string()
    )

    product_table = products.to_table(
        columns=["product_id", "product_locale"]
    )
    product_df = product_table.to_pandas()

    print("\nFull raw catalog product/locale pairs:")
    print(
        product_df.drop_duplicates(["product_id", "product_locale"])
        .groupby("product_locale")
        .size()
        .to_string()
    )

    print("\nDuplicate product/locale keys in raw catalog:")
    print(
        int(
            product_df.duplicated(
                ["product_id", "product_locale"], keep=False
            ).sum()
        )
    )


if __name__ == "__main__":
    main()
