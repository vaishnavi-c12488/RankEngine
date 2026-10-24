
"""View RankEngine dataset features and export small CSV previews."""

from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
PREVIEW = PROCESSED / "previews"

PREVIEW.mkdir(parents=True, exist_ok=True)


def inspect_parquet(path: Path, preview_name: str, columns=None):
    """Print schema and export only the first 100 rows."""
    if not path.exists():
        print(f"\nNOT FOUND: {path}")
        return

    parquet_file = pq.ParquetFile(path)

    print(f"\n{'=' * 65}")
    print(f"FILE: {path.name}")
    print(f"TOTAL ROWS: {parquet_file.metadata.num_rows:,}")
    print(f"COLUMNS: {parquet_file.schema.names}")

    if columns is None:
        columns = parquet_file.schema.names

    batches = parquet_file.iter_batches(
        batch_size=100,
        columns=columns,
    )
    batch = next(batches, None)

    if batch is None:
        print("No data available.")
        return

    sample = batch.to_pandas()
    output_path = PREVIEW / preview_name
    sample.to_csv(output_path, index=False, encoding="utf-8-sig")

    print("\nFEATURE TYPES:")
    print(sample.dtypes.to_string())

    print("\nFIRST 10 ROWS:")
    print(sample.head(10).to_string(index=False, max_colwidth=50))

    print(f"\nCSV PREVIEW SAVED: {output_path}")


def main():
    # Original query-product judgments
    inspect_parquet(
        RAW / "shopping_queries_dataset_examples.parquet",
        "examples_preview.csv",
    )

    # Original product catalog: select useful features
    inspect_parquet(
        RAW / "shopping_queries_dataset_products.parquet",
        "products_preview.csv",
    )

    # Our processed training data
    inspect_parquet(
        PROCESSED / "task1_train.parquet",
        "processed_train_preview.csv",
    )


if __name__ == "__main__":
    main()
