
"""Evaluate BM25 and LambdaMART on the official judged test candidates.

This is a judged-candidate comparison, not a full-catalog retrieval benchmark.
Dense retrieval is evaluated separately once its index is ready.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
from rank_bm25 import BM25Okapi

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from data.tokenization import tokenize
from ranking.ltr_features import build_ltr_features, FEATURE_COLUMNS

TEST_FILE = PROJECT_ROOT / "data" / "processed" / "task1_test.parquet"
MODEL_FILE = PROJECT_ROOT / "ranking" / "model_registry" / "lambdamart.txt"
OUTPUT_FILE = PROJECT_ROOT / "evaluation" / "test_results.json"

RELEVANT_THRESHOLD = 3
K_NDCG = 10
K_PRECISION = 5


def product_text(row: pd.Series) -> str:
    """Combine product fields for lexical BM25 ranking."""
    fields = (
        "product_title",
        "product_bullet_point",
        "product_description",
        "product_brand",
        "product_color",
    )
    parts = []
    for field in fields:
        value = row.get(field, "")
        if isinstance(value, str) and value.strip():
            parts.append(value.strip())
    return " ".join(parts)


def dcg_at_k(labels: list[int], k: int = 10) -> float:
    """Calculate DCG using exponential relevance gain."""
    values = np.asarray(labels[:k], dtype=float)
    if len(values) == 0:
        return 0.0
    discounts = np.log2(np.arange(2, len(values) + 2))
    return float(np.sum((np.power(2.0, values) - 1.0) / discounts))


def query_metrics(ranked_labels: list[int], all_labels: list[int]) -> dict:
    """Compute NDCG@10, MRR, and Precision@5 for one query."""
    ideal = sorted(all_labels, reverse=True)[:K_NDCG]
    ideal_dcg = dcg_at_k(ideal, K_NDCG)
    ndcg = (
        dcg_at_k(ranked_labels, K_NDCG) / ideal_dcg
        if ideal_dcg > 0
        else None
    )

    reciprocal_rank = 0.0
    for position, label in enumerate(ranked_labels, start=1):
        if label >= RELEVANT_THRESHOLD:
            reciprocal_rank = 1.0 / position
            break

    precision = sum(
        label >= RELEVANT_THRESHOLD
        for label in ranked_labels[:K_PRECISION]
    ) / K_PRECISION

    return {
        "ndcg_at_10": ndcg,
        "mrr": reciprocal_rank,
        "precision_at_5": precision,
    }


def summarize(rows: list[dict]) -> dict:
    """Macro-average defined per-query metric values."""
    result = {}
    for metric in ("ndcg_at_10", "mrr", "precision_at_5"):
        values = [
            row[metric] for row in rows
            if row[metric] is not None
        ]
        result[metric] = float(np.mean(values)) if values else None
    result["evaluated_queries"] = len(rows)
    return result


def main() -> None:
    if not TEST_FILE.exists():
        raise FileNotFoundError(f"Test data not found: {TEST_FILE}")
    if not MODEL_FILE.exists():
        raise FileNotFoundError(f"Trained model not found: {MODEL_FILE}")

    print("Loading official test set...", flush=True)
    frame = pd.read_parquet(TEST_FILE)

    required = {
        "query_id", "query", "product_id", "product_locale",
        "relevance", "product_title",
    }
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Test data missing columns: {sorted(missing)}")

    frame = frame.dropna(
        subset=["query_id", "query", "product_locale", "relevance"]
    ).copy()
    frame["relevance"] = pd.to_numeric(
        frame["relevance"], errors="raise"
    ).astype(int)

    group_columns = ["query_id", "product_locale"]
    groups = frame.groupby(group_columns, sort=False, dropna=False)

    print(f"Test rows: {len(frame):,}", flush=True)
    print(f"Test query groups: {len(groups):,}", flush=True)

    print("Loading trained LambdaMART model...", flush=True)
    model = lgb.Booster(model_file=str(MODEL_FILE))

    print("Building ranking features...", flush=True)
    features = build_ltr_features(frame)[FEATURE_COLUMNS]
    frame["_ltr_score"] = model.predict(features)

    results_bm25 = []
    results_ltr = []
    completed = 0

    for _, group in groups:
        group = group.copy()
        all_labels = group["relevance"].astype(int).tolist()

        # BM25 ranks only products judged for this query in the test set.
        # This is not a full-catalog retrieval measurement.
        documents = [
            tokenize(product_text(row))
            for _, row in group.iterrows()
        ]

        if documents and any(documents):
            bm25 = BM25Okapi(documents)
            query_tokens = tokenize(str(group["query"].iloc[0]))
            scores = bm25.get_scores(query_tokens)
            bm25_order = np.argsort(-scores, kind="stable")
        else:
            bm25_order = np.arange(len(group))

        bm25_labels = group["relevance"].to_numpy()[bm25_order].tolist()

        ltr_order = np.argsort(
            -group["_ltr_score"].to_numpy(), kind="stable"
        )
        ltr_labels = group["relevance"].to_numpy()[ltr_order].tolist()

        results_bm25.append(query_metrics(bm25_labels, all_labels))
        results_ltr.append(query_metrics(ltr_labels, all_labels))

        completed += 1
        if completed % 1000 == 0:
            print(f"Evaluated {completed:,} query groups...", flush=True)

    report = {
        "evaluation_scope": (
            "Official test judgments only; BM25 and LambdaMART rank "
            "the judged candidate products for each query. This does not "
            "measure full-catalog retrieval or dense retrieval."
        ),
        "relevant_threshold": RELEVANT_THRESHOLD,
        "bm25_judged_candidates": summarize(results_bm25),
        "lambdamart_judged_candidates": summarize(results_ltr),
    }

    OUTPUT_FILE.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )

    print("\nTest evaluation complete.", flush=True)
    print(json.dumps(report, indent=2), flush=True)
    print(f"Saved report to: {OUTPUT_FILE}", flush=True)


if __name__ == "__main__":
    main()
