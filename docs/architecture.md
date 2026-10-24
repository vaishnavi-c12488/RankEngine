# Architecture

1. **Retrieval**: `retrieval/bi_encoder.py` encodes the query with `sentence-transformers/all-MiniLM-L6-v2`; Qdrant (`data/index/qdrant`, collection `rankengine_products`) returns the nearest products filtered by `product_locale`.
2. **Reranking**: `ranking/ltr_features.py` builds query-product features; the LightGBM LambdaMART model (`ranking/model_registry/lambdamart.txt`) reorders candidates.
3. **API** (`api/main.py`): `POST /search`, `GET /products/{id}?locale=`, `GET /index-info`, `GET /health`. Models and the index are loaded once at startup.
4. **Clients**: React website (`frontend/`) and Streamlit dashboard (`dashboard/`). Both call the API only; neither runs the models.

See the top-level README for run commands, configuration and limitations.
