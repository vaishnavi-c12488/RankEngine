"""API tests for search, product details, index info and CORS.

These tests use a tiny temporary local Qdrant collection with hand-made
vectors, a stubbed query encoder and a stub ranker, so they run offline and
do not need the trained model, the real index or the embedding model.
"""

from __future__ import annotations

import sys
import types

try:  # allow the tests to run without the heavy embedding dependency
    import sentence_transformers  # noqa: F401
except ImportError:
    stub = types.ModuleType("sentence_transformers")
    stub.SentenceTransformer = object
    sys.modules["sentence_transformers"] = stub

import numpy as np
import pytest
from fastapi.testclient import TestClient
from qdrant_client import QdrantClient, models

import api.main as main
from retrieval.index_builder import stable_point_id

PRODUCTS = [
    {
        "product_id": "B000001",
        "product_locale": "us",
        "product_title": "Wireless Headphones Pro",
        "product_description": "<p>Great <b>sound</b></p>",
        "product_bullet_point": "Bluetooth 5.0\n30 hour battery\n\nFoldable",
        "product_brand": "Acme",
        "product_color": "Black",
    },
    {
        "product_id": "B000002",
        "product_locale": "us",
        "product_title": "Running Shoes",
        "product_description": "",
        "product_bullet_point": "",
        "product_brand": "",
        "product_color": "",
    },
    {
        # Same ID as B000001 but in another marketplace: must stay distinct.
        "product_id": "B000001",
        "product_locale": "es",
        "product_title": "Auriculares inalámbricos",
        "product_description": "Sonido excelente",
        "product_bullet_point": "Bluetooth",
        "product_brand": "Acme",
        "product_color": "Negro",
    },
]


class StubRanker:
    def predict(self, features):
        # Prefer the shorter title, deterministic and independent of the model.
        return (-features["title_length"]).to_numpy(dtype=float)


@pytest.fixture()
def client(tmp_path, monkeypatch):
    qdrant = QdrantClient(path=str(tmp_path / "qdrant"))
    qdrant.create_collection(
        collection_name=main.COLLECTION_NAME,
        vectors_config=models.VectorParams(size=4, distance=models.Distance.COSINE),
    )
    qdrant.upsert(
        collection_name=main.COLLECTION_NAME,
        points=[
            models.PointStruct(
                id=stable_point_id(p["product_locale"], p["product_id"]),
                vector=np.random.default_rng(i).random(4).tolist(),
                payload=dict(p, text=p["product_title"]),
            )
            for i, p in enumerate(PRODUCTS)
        ],
        wait=True,
    )

    main.app.state.qdrant = qdrant
    main.app.state.ranker = StubRanker()
    main.app.state.model_features = main.FEATURE_COLUMNS

    monkeypatch.setattr(
        main, "encode_query", lambda *a, **k: np.ones(4, dtype=np.float32)
    )

    # No context manager: the real lifespan (needs the full index) is skipped.
    yield TestClient(main.app)
    qdrant.close()


def test_health(client):
    assert client.get("/health").json()["model_loaded"] is True


def test_search_returns_ranked_results_for_locale(client):
    r = client.post("/search", json={"query": "headphones", "locale": "us"})
    assert r.status_code == 200
    body = r.json()
    assert body["locale"] == "us"
    assert body["candidates_retrieved"] == 2
    assert {x["product_id"] for x in body["results"]} == {"B000001", "B000002"}
    assert [x["rank"] for x in body["results"]] == [1, 2]
    assert all(x["locale"] == "us" for x in body["results"])


def test_search_blank_query_rejected(client):
    assert client.post("/search", json={"query": "   "}).status_code == 422
    assert client.post("/search", json={"query": ""}).status_code == 422


def test_search_invalid_locale_rejected(client):
    r = client.post("/search", json={"query": "x", "locale": "fr"})
    assert r.status_code == 422


def test_search_top_k_cannot_exceed_candidate_k(client):
    r = client.post(
        "/search", json={"query": "x", "top_k": 20, "candidate_k": 10}
    )
    assert r.status_code == 422


def test_product_detail_returns_full_record(client):
    r = client.get("/products/B000001", params={"locale": "us"})
    assert r.status_code == 200
    body = r.json()
    assert body["product_id"] == "B000001"
    assert body["locale"] == "us"
    assert body["title"] == "Wireless Headphones Pro"
    assert body["brand"] == "Acme"
    assert body["color"] == "Black"
    assert body["bullet_points"] == ["Bluetooth 5.0", "30 hour battery", "Foldable"]
    assert body["description"] == "<p>Great <b>sound</b></p>"


def test_product_detail_is_keyed_by_id_and_locale(client):
    us = client.get("/products/B000001", params={"locale": "us"}).json()
    es = client.get("/products/B000001", params={"locale": "es"}).json()
    assert us["title"] != es["title"]
    assert es["title"] == "Auriculares inalámbricos"


def test_product_detail_missing_fields_stay_empty(client):
    body = client.get("/products/B000002", params={"locale": "us"}).json()
    assert body["description"] == ""
    assert body["bullet_points"] == []
    assert body["brand"] == ""
    assert body["color"] == ""


def test_product_detail_unknown_id_is_404(client):
    r = client.get("/products/DOES_NOT_EXIST", params={"locale": "us"})
    assert r.status_code == 404


def test_product_exists_only_in_its_own_locale(client):
    # B000002 is indexed for "us" only.
    assert client.get("/products/B000002", params={"locale": "jp"}).status_code == 404


def test_product_detail_invalid_locale_is_422(client):
    assert client.get("/products/B000001", params={"locale": "xx"}).status_code == 422


def test_product_detail_defaults_to_us(client):
    assert client.get("/products/B000001").json()["locale"] == "us"


def test_index_info_reports_metadata(client, tmp_path, monkeypatch):
    meta = tmp_path / "index_metadata.json"
    meta.write_text(
        '{"product_count": 15000, "locales": {"us": 5000, "jp": 5000, "es": 5000},'
        ' "development_subset": true, "limit_per_locale": 5000,'
        ' "model": "sentence-transformers/all-MiniLM-L6-v2"}',
        encoding="utf-8",
    )
    monkeypatch.setattr(main, "INDEX_METADATA_PATH", meta)
    body = client.get("/index-info").json()
    assert body["product_count"] == 15000
    assert body["development_subset"] is True
    assert body["locales"]["jp"] == 5000


def test_index_info_without_metadata_file(client, tmp_path, monkeypatch):
    monkeypatch.setattr(main, "INDEX_METADATA_PATH", tmp_path / "missing.json")
    body = client.get("/index-info").json()
    assert body["product_count"] is None


def test_cors_allows_vite_dev_origin(client):
    r = client.options(
        "/search",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert r.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_cors_rejects_unknown_origin(client):
    r = client.options(
        "/search",
        headers={
            "Origin": "http://evil.example",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert "access-control-allow-origin" not in r.headers


def test_split_bullet_points():
    assert main.split_bullet_points("a\n\n b \n") == ["a", "b"]
    assert main.split_bullet_points("") == []
