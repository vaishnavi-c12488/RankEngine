from pathlib import Path
import pandas as pd
from qdrant_client import QdrantClient

root = Path.cwd()
products = pd.read_parquet(root / "data" / "raw" / "shopping_queries_dataset_products.parquet")
client = QdrantClient(path=str(root / "data" / "index" / "qdrant"))

print("FULL CATALOG")
print("Rows:", f"{len(products):,}")
print("Unique product IDs:", f"{products['product_id'].astype(str).nunique():,}")
print("Locale counts:")
print(products["product_locale"].value_counts().to_string())

print("\nINDEX PAYLOAD SAMPLE")
points, _ = client.scroll(
    collection_name="rankengine_products",
    limit=5,
    with_payload=True,
    with_vectors=False,
)
for p in points:
    print(p.payload)
