
"""Build a persistent Qdrant product index for RankEngine."""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path

import pandas as pd
from qdrant_client import QdrantClient, models

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from retrieval.bi_encoder import DEFAULT_MODEL, encode_products

RAW_PRODUCTS = (
    ROOT / "data" / "raw" / "shopping_queries_dataset_products.parquet"
)
INDEX_DIR = ROOT / "data" / "index" / "qdrant_full"
COLLECTION = "rankengine_products"


def load_products(limit_per_locale: int | None = None) -> pd.DataFrame:
    """Load the catalog and optionally sample products from each locale."""
    if limit_per_locale is not None and limit_per_locale < 1:
        raise ValueError("limit_per_locale must be positive")

    print(f"Reading catalog: {RAW_PRODUCTS}", flush=True)
    df = pd.read_parquet(RAW_PRODUCTS)
    print(f"Loaded {len(df):,} raw rows.", flush=True)

    required = {"product_id", "product_locale", "product_title"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing catalog columns: {sorted(missing)}")

    df = df.dropna(subset=["product_id", "product_locale"]).copy()
    df["product_id"] = df["product_id"].astype(str)
    df["product_locale"] = df["product_locale"].astype(str)

    text_columns = [
        column
        for column in [
            "product_title",
            "product_bullet_point",
            "product_description",
            "product_brand",
            "product_color",
        ]
        if column in df.columns
    ]

    for column in text_columns:
        df[column] = df[column].fillna("").astype(str).str.strip()

    df = df.drop_duplicates(
        subset=["product_id", "product_locale"],
        keep="first",
    )

    if limit_per_locale is not None:
        sampled_parts = []
        for locale, locale_frame in df.groupby("product_locale", sort=True):
            sample_size = min(len(locale_frame), limit_per_locale)
            sampled = locale_frame.sample(
                n=sample_size,
                random_state=42,
            )
            sampled_parts.append(sampled)
            print(
                f"Selected {len(sampled):,} products for locale {locale}.",
                flush=True,
            )
        df = pd.concat(sampled_parts, ignore_index=True)

    df["text"] = (
        df[text_columns]
        .agg(" ".join, axis=1)
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
    )
    df = df.loc[df["text"].ne("")].reset_index(drop=True)

    print(f"Prepared {len(df):,} products.", flush=True)
    return df


def stable_point_id(locale: str, product_id: str) -> str:
    """Return a reproducible Qdrant point ID for a product-locale pair."""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"{locale}:{product_id}"))


def build_index(
    model_name: str = DEFAULT_MODEL,
    batch_size: int = 256,
    limit_per_locale: int | None = None,
) -> int:
    """Encode products and store their vectors in local Qdrant."""
    if batch_size < 1:
        raise ValueError("batch_size must be positive")

    products = load_products(limit_per_locale)
    if products.empty:
        raise ValueError("No usable products found in the catalog.")

    print("Loading embedding model...", flush=True)
    dimension = len(
        encode_products(
            ["embedding dimension check"],
            model_name=model_name,
            batch_size=1,
        )[0]
    )
    print(f"Vector dimension: {dimension}", flush=True)

    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    client = QdrantClient(path=str(INDEX_DIR))

    try:
        # The target collection is intentionally rebuilt by this script.
        if client.collection_exists(COLLECTION):
            print(f"Removing existing collection: {COLLECTION}", flush=True)
            client.delete_collection(COLLECTION)

        client.create_collection(
            collection_name=COLLECTION,
            vectors_config=models.VectorParams(
                size=dimension,
                distance=models.Distance.COSINE,
            ),
        )

        total = len(products)

        for start in range(0, total, batch_size):
            end = min(start + batch_size, total)
            batch = products.iloc[start:end]

            print(
                f"Encoding products {start + 1:,}â€“{end:,} of {total:,}...",
                flush=True,
            )

            vectors = encode_products(
                batch["text"].tolist(),
                model_name=model_name,
                batch_size=min(32, batch_size),
            )

            points = []
            for position, (_, row) in enumerate(batch.iterrows()):
                locale = row["product_locale"]
                product_id = row["product_id"]

                payload = {
                    "product_id": product_id,
                    "product_locale": locale,
                    "product_title": row.get("product_title", ""),
                    "product_description": row.get("product_description", ""),
                    "product_bullet_point": row.get(
                        "product_bullet_point", ""
                    ),
                    "product_brand": row.get("product_brand", ""),
                    "product_color": row.get("product_color", ""),
                    "text": row["text"],
                }

                points.append(
                    models.PointStruct(
                        id=stable_point_id(locale, product_id),
                        vector=vectors[position].tolist(),
                        payload=payload,
                    )
                )

            print(f"Writing products {start + 1:,}â€“{end:,}...", flush=True)
            client.upsert(
                collection_name=COLLECTION,
                points=points,
                wait=True,
            )
            print(f"Indexed {end:,}/{total:,}.", flush=True)

        metadata = {
            "collection": COLLECTION,
            "model": model_name,
            "product_count": total,
            "locales": {
                str(locale): int(count)
                for locale, count in
                products["product_locale"].value_counts().items()
            },
            "vector_size": dimension,
            "development_subset": limit_per_locale is not None,
            "limit_per_locale": limit_per_locale,
        }

        (INDEX_DIR / "index_metadata.json").write_text(
            json.dumps(metadata, indent=2),
            encoding="utf-8",
        )

        print("\nIndex built successfully.", flush=True)
        print(json.dumps(metadata, indent=2), flush=True)
        return total

    finally:
        client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--limit-per-locale", type=int, default=None)
    args = parser.parse_args()

    build_index(
        model_name=args.model,
        batch_size=args.batch_size,
        limit_per_locale=args.limit_per_locale,
    )

