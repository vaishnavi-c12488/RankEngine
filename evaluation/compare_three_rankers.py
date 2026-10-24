"""Compare BM25, bi-encoder, and LambdaMART on judged test candidates.

This is a judged-candidate ranking comparison, NOT full-catalog retrieval.
"""
import json
import sys
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
from rank_bm25 import BM25Okapi

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data.tokenization import tokenize
from ranking.ltr_features import build_ltr_features, FEATURE_COLUMNS
from retrieval.bi_encoder import encode_texts

TEST = ROOT / "data" / "processed" / "task1_test.parquet"
MODEL = ROOT / "ranking" / "model_registry" / "lambdamart.txt"
OUTPUT = ROOT / "evaluation" / "three_ranker_results.json"
THRESHOLD = 3


def product_text(row):
    fields = [
        "product_title", "product_bullet_point",
        "product_description", "product_brand", "product_color",
    ]
    return " ".join(
        str(row.get(f, "")).strip()
        for f in fields
        if isinstance(row.get(f, ""), str) and row.get(f, "").strip()
    )


def metrics(ranked, all_labels):
    def dcg(labels):
        labels = np.asarray(labels[:10], dtype=float)
        if not len(labels):
            return 0.0
        return float(np.sum((2**labels - 1) / np.log2(np.arange(2, len(labels) + 2))))

    ideal = sorted(all_labels, reverse=True)[:10]
    idcg = dcg(ideal)
    ndcg = dcg(ranked) / idcg if idcg else None
    rr = next(
        (1 / i for i, label in enumerate(ranked, 1) if label >= THRESHOLD),
        0.0,
    )
    p5 = sum(label >= THRESHOLD for label in ranked[:5]) / 5
    return {"ndcg_at_10": ndcg, "mrr": rr, "precision_at_5": p5}


def summarize(rows):
    result = {}
    for key in ("ndcg_at_10", "mrr", "precision_at_5"):
        values = [r[key] for r in rows if r[key] is not None]
        result[key] = float(np.mean(values)) if values else None
    result["evaluated_queries"] = len(rows)
    return result



def main():
    if not TEST.exists() or not MODEL.exists():
        raise FileNotFoundError("Test parquet or LambdaMART model is missing.")

    print("Loading test judgments...", flush=True)
    frame = pd.read_parquet(TEST)
    frame = frame.dropna(
        subset=["query_id", "query", "product_locale", "relevance"]
    ).copy()
    frame["relevance"] = pd.to_numeric(frame["relevance"]).astype(int)

    # Fixed reproducible sample of query groups; retain all judged candidates
    # belonging to each selected query group.
    group_keys = frame[["query_id", "product_locale"]].drop_duplicates()
    sample_keys = group_keys.sample(
        n=min(500, len(group_keys)), random_state=42
    )
    frame = frame.merge(
        sample_keys, on=["query_id", "product_locale"], how="inner"
    ).reset_index(drop=True)

    print(
        f"Sample: {len(frame):,} judged rows across "
        f"{len(sample_keys):,} query groups.",
        flush=True,
    )

    print("Preparing unique product texts...", flush=True)
    texts = [product_text(row) for _, row in frame.iterrows()]
    unique_texts = list(dict.fromkeys(texts))
    print(f"Encoding {len(unique_texts):,} unique products...", flush=True)
    unique_vectors = encode_texts(unique_texts, batch_size=64)
    vector_by_text = {
        text: unique_vectors[i] for i, text in enumerate(unique_texts)
    }
    product_vectors = np.stack([vector_by_text[t] for t in texts])

    print("Encoding sampled unique queries...", flush=True)
    groups = frame.groupby(["query_id", "product_locale"], sort=False)
    queries = list(dict.fromkeys(
        str(group["query"].iloc[0]) for _, group in groups
    ))
    query_vectors = encode_texts(queries, batch_size=64)
    query_vector_by_text = {
        query: query_vectors[i] for i, query in enumerate(queries)
    }

    print("Scoring LambdaMART...", flush=True)
    booster = lgb.Booster(model_file=str(MODEL))
    frame["_ltr_score"] = booster.predict(
        build_ltr_features(frame)[FEATURE_COLUMNS]
    )

    results = {"bm25": [], "bi_encoder": [], "lambdamart": []}
    for n, (_, group) in enumerate(
        frame.groupby(["query_id", "product_locale"], sort=False), 1
    ):
        positions = group.index.to_numpy()
        labels = group["relevance"].to_numpy().astype(int)
        query = str(group["query"].iloc[0])

        docs = [tokenize(product_text(row)) for _, row in group.iterrows()]
        if docs and any(docs):
            bm25 = BM25Okapi(docs)
            bm25_order = np.argsort(
                -bm25.get_scores(tokenize(query)), kind="stable"
            )
        else:
            bm25_order = np.arange(len(group))

        dense_scores = product_vectors[positions] @ query_vector_by_text[query]
        dense_order = np.argsort(-dense_scores, kind="stable")
        ltr_order = np.argsort(
            -group["_ltr_score"].to_numpy(), kind="stable"
        )

        for name, order in (
            ("bm25", bm25_order),
            ("bi_encoder", dense_order),
            ("lambdamart", ltr_order),
        ):
            results[name].append(metrics(labels[order].tolist(), labels.tolist()))

        if n % 100 == 0:
            print(f"Evaluated {n}/{len(sample_keys)} groups.", flush=True)

    report = {
        "scope": (
            "Reproducible 500-query-group sample of official test judgments. "
            "All judged candidates for sampled queries are ranked. This is "
            "not full-test evaluation, full-catalog retrieval, or Recall@K."
        ),
        "sample_seed": 42,
        "sampled_query_groups": len(sample_keys),
        "sampled_judged_rows": len(frame),
        "relevance_mapping": {"E": 3, "S": 2, "C": 1, "I": 0},
        "binary_relevant_threshold": THRESHOLD,
        "product_encoder": "sentence-transformers/all-MiniLM-L6-v2",
        "results": {name: summarize(rows) for name, rows in results.items()},
    }
    output = ROOT / "evaluation" / "three_ranker_sample_results.json"
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2), flush=True)
    print(f"Saved: {output}", flush=True)


if __name__ == "__main__":
    main()
