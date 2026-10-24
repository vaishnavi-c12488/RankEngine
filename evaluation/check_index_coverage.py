from pathlib import Path
import pandas as pd
from qdrant_client import QdrantClient

ROOT = Path.cwd()
TEST = ROOT / "data" / "processed" / "task1_test.parquet"
INDEX = ROOT / "data" / "index" / "qdrant"
COLLECTION = "rankengine_products"

if not TEST.exists():
    matches = list((ROOT / "data").rglob("task1_test.parquet"))
    if not matches:
        raise FileNotFoundError("Could not find task1_test.parquet under data/")
    TEST = matches[0]

df = pd.read_parquet(TEST)
df["query"] = df["query"].astype(str)
df["product_id"] = df["product_id"].astype(str)
df["relevance"] = pd.to_numeric(df["relevance"], errors="coerce")
sample = df[["query"]].drop_duplicates().sample(n=min(500, df["query"].nunique()), random_state=42)
sampled = df.merge(sample, on="query")
relevant = sampled.loc[sampled["relevance"] >= 3, ["product_id", "product_locale"]].drop_duplicates()

client = QdrantClient(path=str(INDEX))
info = client.get_collection(COLLECTION)
indexed = set()
offset = None
while True:
    points, offset = client.scroll(
        collection_name=COLLECTION,
        limit=1000,
        offset=offset,
        with_payload=["product_id", "product_locale"],
        with_vectors=False,
    )
    for p in points:
        payload = p.payload or {}
        pid = payload.get("product_id")
        loc = payload.get("product_locale")
        if pid is not None and loc is not None:
            indexed.add((str(pid), str(loc)))
    if offset is None:
        break

relevant_pairs = set(zip(relevant["product_id"], relevant["product_locale"].astype(str)))
present = relevant_pairs & indexed
print(f"Test file: {TEST}")
print(f"Index points: {info.points_count:,}")
print(f"Sampled queries: {sample['query'].nunique():,}")
print(f"Unique exact-relevant product/locale pairs: {len(relevant_pairs):,}")
print(f"Relevant pairs present in index: {len(present):,}")
print(f"Relevant pairs missing from index: {len(relevant_pairs - indexed):,}")
print(f"Index coverage of relevant pairs: {100 * len(present) / max(1, len(relevant_pairs)):.2f}%")
