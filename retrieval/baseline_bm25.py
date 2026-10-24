
"""BM25 lexical ranking baseline for RankEngine evaluation."""

from pathlib import Path
import sys

import pandas as pd
from rank_bm25 import BM25Okapi


# Make the project root importable when this script is run directly.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from data.tokenization import tokenize


TRAIN_FILE = PROJECT_ROOT / "data" / "processed" / "task1_train.parquet"
TEST_FILE = PROJECT_ROOT / "data" / "processed" / "task1_test.parquet"


def product_text(frame: pd.DataFrame) -> pd.Series:
    """Combine available product text fields."""
    columns = [
        "product_title",
        "product_description",
        "product_bullet_point",
        "product_brand",
        "product_color",
    ]

    available_columns = [
        column for column in columns if column in frame.columns
    ]

    if not available_columns:
        return pd.Series("", index=frame.index, dtype=str)

    return (
        frame[available_columns]
        .fillna("")
        .astype(str)
        .agg(" ".join, axis=1)
        .str.strip()
    )


def rank_query_products(
    query: str,
    candidates: pd.DataFrame,
) -> pd.DataFrame:
    """Rank the supplied candidate products using BM25."""
    if candidates.empty:
        result = candidates.copy()
        result["bm25_score"] = pd.Series(dtype=float)
        return result

    documents = product_text(candidates)
    tokenized_documents = [
        tokenize(text) for text in documents
    ]

    ranked = candidates.copy()

    if not any(tokenized_documents):
        ranked["bm25_score"] = 0.0
    else:
        model = BM25Okapi(tokenized_documents)
        scores = model.get_scores(tokenize(query))
        ranked["bm25_score"] = scores

    return ranked.sort_values(
        by=["bm25_score", "product_id"],
        ascending=[False, True],
        kind="stable",
    )


def main() -> None:
    """Run a BM25 smoke test on one test query."""
    if not TRAIN_FILE.exists() or not TEST_FILE.exists():
        raise FileNotFoundError(
            "Processed data not found. "
            "Run data/preprocessing.py first."
        )

    test = pd.read_parquet(TEST_FILE)

    if test.empty:
        raise ValueError("The processed test dataset is empty.")

    first_row = test.iloc[0]
    query = first_row["query"]
    query_id = first_row["query_id"]
    locale = first_row["product_locale"]

    candidates = test.loc[
        (test["query_id"] == query_id)
        & (test["product_locale"] == locale)
    ].copy()

    ranked = rank_query_products(query, candidates)

    print("BM25 smoke test completed.")
    print("Query:", query)
    print("Locale:", locale)
    print("Candidate products:", len(candidates))
    print("\nTop 5 ranked products:")

    columns = [
        column
        for column in [
            "product_id",
            "product_title",
            "bm25_score",
            "esci_label",
        ]
        if column in ranked.columns
    ]

    print(ranked[columns].head(5).to_string(index=False))
    print(
        "\nScope: judged candidates only; "
        "this is not a full-catalog evaluation."
    )


if __name__ == "__main__":
    main()
