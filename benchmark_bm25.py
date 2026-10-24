
"""Benchmark the existing BM25 baseline on 50 test queries.

This is a timing check only, not a full-catalog relevance evaluation.
It uses the existing judged candidates and does not modify project data.
"""

from pathlib import Path
from time import perf_counter

import pandas as pd

from retrieval.baseline_bm25 import rank_query_products


PROJECT_ROOT = Path(__file__).resolve().parent
TEST_FILE = PROJECT_ROOT / "data" / "processed" / "task1_test.parquet"
N_QUERIES = 50


def main() -> None:
    if not TEST_FILE.exists():
        raise FileNotFoundError(f"Test file not found: {TEST_FILE}")

    test = pd.read_parquet(TEST_FILE)

    required = {"query_id", "query", "product_locale", "product_id"}
    missing = required - set(test.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    # Select up to 50 distinct queries, spreading the sample across locales.
    query_table = (
        test[["query_id", "query", "product_locale"]]
        .drop_duplicates(subset=["query_id", "product_locale"])
    )

    per_locale = max(1, N_QUERIES // query_table["product_locale"].nunique())
    sampled = (
        query_table.groupby("product_locale", group_keys=False)
        .head(per_locale)
        .head(N_QUERIES)
    )

    total_candidates = 0
    start = perf_counter()

    for _, item in sampled.iterrows():
        candidates = test.loc[
            (test["query_id"] == item["query_id"])
            & (test["product_locale"] == item["product_locale"])
        ]
        rank_query_products(item["query"], candidates)
        total_candidates += len(candidates)

    elapsed = perf_counter() - start

    print("BM25 timing check completed.")
    print("Queries timed:", len(sampled))
    print("Locales:", sampled["product_locale"].value_counts().to_dict())
    print("Judged candidates scored:", total_candidates)
    print(f"Elapsed seconds: {elapsed:.2f}")
    print(f"Seconds per query: {elapsed / max(1, len(sampled)):.4f}")
    print(
        "Note: this times judged-candidate scoring only, "
        "not full-catalog retrieval."
    )


if __name__ == "__main__":
    main()
