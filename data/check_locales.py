
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"

for filename in ["task1_train.parquet", "task1_test.parquet"]:
    path = PROCESSED / filename

    df = pd.read_parquet(
        path,
        columns=["product_locale", "query"],
    )

    print(f"\n{'=' * 50}")
    print(f"FILE: {filename}")
    print("\nRows per locale:")
    print(df["product_locale"].value_counts(dropna=False).to_string())
    print("\nUnique query texts:", df["query"].nunique())
    print("\nSample queries:")
    print(df["query"].drop_duplicates().head(10).to_string(index=False))
