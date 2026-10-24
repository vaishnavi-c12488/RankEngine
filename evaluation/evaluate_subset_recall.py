import json
import sys
from pathlib import Path

import pandas as pd
from qdrant_client import QdrantClient, models

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from retrieval.bi_encoder import encode_query, DEFAULT_MODEL

TEST = ROOT / "data" / "processed" / "task1_test.parquet"
INDEX = ROOT / "data" / "index" / "qdrant"
OUTPUT = ROOT / "evaluation" / "subset_recall_results.json"
COLLECTION = "rankengine_products"
KS = (10, 50, 100)
THRESHOLD = 3
SAMPLE_SIZE = 500

def main():
    if not TEST.exists():
        raise FileNotFoundError(f"Test set missing: {TEST}")
    if not INDEX.exists():
        raise FileNotFoundError(f"Local Qdrant index missing: {INDEX}")

    frame = pd.read_parquet(TEST)
    frame = frame.dropna(
        subset=["query_id", "query", "product_id", "product_locale", "relevance"]
    ).copy()
    frame["product_id"] = frame["product_id"].astype(str)
    frame["relevance"] = pd.to_numeric(frame["relevance"]).astype(int)

    groups = frame.groupby(["query_id", "product_locale"], sort=False)
    keys = pd.DataFrame(
        [{"query_id": qid, "product_locale": locale}
         for qid, locale in groups.groups]
    )
    sample = keys.sample(n=min(SAMPLE_SIZE, len(keys)), random_state=42)

    client = QdrantClient(path=str(INDEX))
    totals = {k: 0.0 for k in KS}
    evaluated = 0
    no_relevant = 0

    try:
        if not client.collection_exists(COLLECTION):
            raise RuntimeError(f"Collection not found: {COLLECTION}")

        info = client.get_collection(COLLECTION)
        print(f"Index points: {info.points_count:,}", flush=True)

        for _, key in sample.iterrows():
            qid, locale = key["query_id"], key["product_locale"]
            group = frame[
                (frame["query_id"] == qid) &
                (frame["product_locale"] == locale)
            ]
            relevant = set(
                group.loc[group["relevance"] >= THRESHOLD, "product_id"]
            )
            if not relevant:
                no_relevant += 1
                continue

            query = str(group["query"].iloc[0])
            vector = encode_query(query, model_name=DEFAULT_MODEL)

            max_k = max(KS)
            result = client.query_points(
                collection_name=COLLECTION,
                query=vector.tolist(),
                query_filter=models.Filter(must=[models.FieldCondition(key="product_locale", match=models.MatchValue(value=locale))]),
                limit=max_k,
                with_payload=True,
                with_vectors=False,
            )

            retrieved_ids = [
                str((point.payload or {}).get("product_id", ""))
                for point in result.points
            ]

            for k in KS:
                hits = len(relevant.intersection(retrieved_ids[:k]))
                totals[k] += hits / len(relevant)

            evaluated += 1
            if evaluated % 100 == 0:
                print(f"Evaluated {evaluated} query groups...", flush=True)

    finally:
        client.close()

    report = {
        "scope": (
            "Development-subset Qdrant index only; not full-catalog retrieval. "
            "Recall is measured against exact-relevant (E, relevance >= 3) "
            "judged products. Relevant products absent from the index count "
            "as missed."
        ),
        "index_path": str(INDEX),
        "sample_seed": 42,
        "sampled_query_groups": len(sample),
        "evaluated_query_groups": evaluated,
        "groups_without_exact_relevant_judgments": no_relevant,
        "relevance_threshold": THRESHOLD,
        "recall_at_k": {
            str(k): totals[k] / evaluated if evaluated else None
            for k in KS
        },
    }

    OUTPUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2), flush=True)
    print(f"Saved: {OUTPUT}", flush=True)

if __name__ == "__main__":
    main()



