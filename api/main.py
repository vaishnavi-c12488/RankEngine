
"""RankEngine search API: Qdrant retrieval followed by LambdaMART reranking."""
from __future__ import annotations

import json
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

import lightgbm as lgb
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from qdrant_client import QdrantClient, models

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from retrieval.bi_encoder import DEFAULT_MODEL, encode_query
from retrieval.index_builder import stable_point_id
from ranking.ltr_features import FEATURE_COLUMNS, build_ltr_features

INDEX_DIR = ROOT / "data" / "index" / "qdrant"
INDEX_METADATA_PATH = INDEX_DIR / "index_metadata.json"
MODEL_PATH = ROOT / "ranking" / "model_registry" / "lambdamart.txt"

COLLECTION_NAME = "rankengine_products"
DEFAULT_TOP_K = 50
MAX_RESULTS = 100

DEFAULT_CORS_ORIGINS = (
    "http://localhost:5173,http://127.0.0.1:5173"
)

Locale = Literal["us", "jp", "es"]


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    locale: Locale = "us"
    top_k: int = Field(default=10, ge=1, le=MAX_RESULTS)
    candidate_k: int = Field(default=DEFAULT_TOP_K, ge=1, le=MAX_RESULTS)


class SearchResult(BaseModel):
    rank: int
    product_id: str
    locale: str
    title: str
    description: str = ""
    brand: str = ""
    retrieval_score: float
    rerank_score: float


class SearchResponse(BaseModel):
    query: str
    locale: str
    candidates_retrieved: int
    results: list[SearchResult]


class ProductDetail(BaseModel):
    """Full catalog record for one product, as stored in the index payload."""

    product_id: str
    locale: str
    title: str
    description: str = ""
    bullet_points: list[str] = Field(default_factory=list)
    brand: str = ""
    color: str = ""


class IndexInfo(BaseModel):
    product_count: int | None = None
    locales: dict[str, int] = Field(default_factory=dict)
    development_subset: bool | None = None
    limit_per_locale: int | None = None
    embedding_model: str = DEFAULT_MODEL


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load the configured Qdrant collection and LambdaMART model."""
    if not MODEL_PATH.is_file():
        raise RuntimeError(f"LambdaMART model not found: {MODEL_PATH}")

    qdrant_url = os.getenv("QDRANT_URL", "").strip()
    qdrant_api_key = os.getenv("QDRANT_API_KEY", "").strip()

    if qdrant_url:
        # Server mode supports Qdrant Cloud and local Docker Qdrant.
        client = QdrantClient(
            url=qdrant_url,
            api_key=qdrant_api_key or None,
            timeout=60,
        )
    else:
        # Preserve the existing embedded local index.
        if not INDEX_DIR.is_dir():
            raise RuntimeError(
                f"Qdrant index directory not found: {INDEX_DIR}"
            )
        client = QdrantClient(path=str(INDEX_DIR))

    try:
        if not client.collection_exists(COLLECTION_NAME):
            raise RuntimeError(
                f"Qdrant collection '{COLLECTION_NAME}' does not exist."
            )

        model = lgb.Booster(model_file=str(MODEL_PATH))
        model_features = model.feature_name()

        missing = [
            name for name in model_features
            if name not in FEATURE_COLUMNS
        ]
        if missing:
            raise RuntimeError(
                "The trained model expects features not supplied by "
                f"ranking/ltr_features.py: {missing}"
            )

        app.state.qdrant = client
        app.state.ranker = model
        app.state.model_features = model_features

        yield
    finally:
        client.close()


app = FastAPI(
    title="RankEngine Search API",
    description=(
        "Product search using dense bi-encoder retrieval and "
        "LightGBM LambdaMART reranking."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

_cors_origins = [
    origin.strip()
    for origin in os.getenv(
        "RANKENGINE_CORS_ORIGINS",
        DEFAULT_CORS_ORIGINS,
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


def split_bullet_points(raw: str) -> list[str]:
    """Split the catalog's newline-separated bullet text into items."""
    return [
        line.strip()
        for line in (raw or "").splitlines()
        if line.strip()
    ]


@app.get("/health")
def health():
    """Basic service and model status."""
    return {
        "status": "ok",
        "collection": COLLECTION_NAME,
        "model_loaded": hasattr(app.state, "ranker"),
    }


@app.get("/index-info", response_model=IndexInfo)
def index_info():
    """Describe the indexed catalog and embedding model."""
    try:
        meta = json.loads(
            INDEX_METADATA_PATH.read_text(encoding="utf-8")
        )
    except (OSError, ValueError):
        return IndexInfo()

    return IndexInfo(
        product_count=meta.get("product_count"),
        locales=meta.get("locales") or {},
        development_subset=meta.get("development_subset"),
        limit_per_locale=meta.get("limit_per_locale"),
        embedding_model=meta.get("model") or DEFAULT_MODEL,
    )


@app.get("/products/{product_id}", response_model=ProductDetail)
def get_product(product_id: str, locale: Locale = "us"):
    """Return one indexed product, looked up by product ID and locale."""
    product_id = product_id.strip()
    if not product_id or len(product_id) > 64:
        raise HTTPException(
            status_code=422,
            detail="Invalid product ID.",
        )

    try:
        points = app.state.qdrant.retrieve(
            collection_name=COLLECTION_NAME,
            ids=[stable_point_id(locale, product_id)],
            with_payload=True,
            with_vectors=False,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Product lookup failed: {type(exc).__name__}",
        ) from exc

    payload = (points[0].payload or {}) if points else {}

    if (
        not payload
        or str(payload.get("product_id")) != product_id
        or str(payload.get("product_locale")) != locale
    ):
        raise HTTPException(
            status_code=404,
            detail=(
                f"Product '{product_id}' not found in "
                f"marketplace '{locale}'."
            ),
        )

    return ProductDetail(
        product_id=product_id,
        locale=locale,
        title=str(payload.get("product_title") or ""),
        description=str(payload.get("product_description") or ""),
        bullet_points=split_bullet_points(
            str(payload.get("product_bullet_point") or "")
        ),
        brand=str(payload.get("product_brand") or ""),
        color=str(payload.get("product_color") or ""),
    )


@app.post("/search", response_model=SearchResponse)
def search_products(request: SearchRequest):
    """Retrieve products for a locale and rerank them with LambdaMART."""
    query = request.query.strip()
    if not query:
        raise HTTPException(
            status_code=422,
            detail="Query cannot be blank.",
        )

    if request.top_k > request.candidate_k:
        raise HTTPException(
            status_code=422,
            detail="top_k cannot exceed candidate_k.",
        )

    try:
        vector = encode_query(query, model_name=DEFAULT_MODEL)

        retrieved = app.state.qdrant.query_points(
            collection_name=COLLECTION_NAME,
            query=vector.tolist(),
            query_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="product_locale",
                        match=models.MatchValue(value=request.locale),
                    )
                ]
            ),
            limit=request.candidate_k,
            with_payload=True,
            with_vectors=False,
        )

        points = retrieved.points
        if not points:
            return SearchResponse(
                query=query,
                locale=request.locale,
                candidates_retrieved=0,
                results=[],
            )

        records = []
        for point in points:
            payload = point.payload or {}
            records.append(
                {
                    "product_id": str(payload.get("product_id", "")),
                    "product_locale": str(
                        payload.get("product_locale", request.locale)
                    ),
                    "product_title": str(
                        payload.get("product_title") or ""
                    ),
                    "product_description": str(
                        payload.get("product_description") or ""
                    ),
                    "product_bullet_point": str(
                        payload.get("product_bullet_point") or ""
                    ),
                    "product_brand": str(
                        payload.get("product_brand") or ""
                    ),
                    "product_color": str(
                        payload.get("product_color") or ""
                    ),
                    "text": str(payload.get("text") or ""),
                    "retrieval_score": float(point.score or 0.0),
                }
            )

        candidates = pd.DataFrame(records)
        candidates["query"] = query

        features = build_ltr_features(candidates)
        features = features.reindex(
            columns=app.state.model_features,
            fill_value=0,
        )
        scores = app.state.ranker.predict(features)

        candidates["rerank_score"] = scores
        candidates = candidates.sort_values(
            by=["rerank_score", "retrieval_score"],
            ascending=[False, False],
            kind="stable",
        ).head(request.top_k)

        results = []
        for rank, (_, row) in enumerate(
            candidates.iterrows(),
            start=1,
        ):
            results.append(
                SearchResult(
                    rank=rank,
                    product_id=row["product_id"],
                    locale=row["product_locale"],
                    title=row["product_title"],
                    description=row["product_description"],
                    brand=row["product_brand"],
                    retrieval_score=row["retrieval_score"],
                    rerank_score=float(row["rerank_score"]),
                )
            )

        return SearchResponse(
            query=query,
            locale=request.locale,
            candidates_retrieved=len(points),
            results=results,
        )

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {type(exc).__name__}: {exc}",
        ) from exc
