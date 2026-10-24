# RankEngine

AI-powered product search: dense bi-encoder retrieval (Qdrant) followed by LightGBM LambdaMART reranking, served by FastAPI, with a React website and the original Streamlit dashboard.

```
User query → FastAPI /search → query embedding → Qdrant retrieval → LambdaMART rerank → ranked results
                                                                          ↓
                         React website: results grid → product details (GET /products/{id}?locale=)
```

## Quick start

Prerequisites: Python 3.10+, Node.js 18+ (developed on Node 22), and a built index + trained model
(`data/index/qdrant/`, `ranking/model_registry/lambdamart.txt`).

```bash
# 1. Backend (terminal 1, from the project root)
pip install -r requirements.txt
python -m uvicorn api.main:app --reload          # http://127.0.0.1:8000  (docs at /docs)

# 2. Website (terminal 2)
cd frontend
npm install
cp .env.example .env                              # optional: set VITE_API_URL
npm run dev                                       # http://localhost:5173

# Optional: original Streamlit dashboard (still works)
streamlit run dashboard/streamlit_search_demo.py
```

## Configuration

| Variable | Where | Default | Purpose |
|---|---|---|---|
| `VITE_API_URL` | frontend `.env` | `http://127.0.0.1:8000` | Backend base URL |
| `RANKENGINE_CORS_ORIGINS` | backend env | `http://localhost:5173,http://127.0.0.1:5173` | Comma-separated browser origins allowed to call the API |
| `RANKENGINE_API_URL` | Streamlit env | `http://127.0.0.1:8000` | Backend URL for the dashboard |

For a production build: `cd frontend && npm run build` (output in `frontend/dist/`), and add the site's origin to `RANKENGINE_CORS_ORIGINS`.

## Backend API

The `/search` and `/health` contracts are unchanged. Added:

- `GET /products/{product_id}?locale=us|jp|es` returns the full indexed record: `product_id`, `locale`, `title`, `description` (raw, may contain HTML), `bullet_points` (list, split from the catalog's newline-separated text), `brand`, `color`. The record is fetched directly by the stable Qdrant point ID (`uuid5("{locale}:{product_id}")`, the same function the index builder uses), never by re-running a search. Returns 404 if the product is not in that marketplace, 422 for an invalid locale.
- `GET /index-info` returns index size, per-locale counts and whether it is a development subset (read from `index_metadata.json`; no filesystem paths are exposed).
- CORS middleware, configured as above.

## Frontend architecture (`frontend/`)

React 18 + TypeScript + Vite + Tailwind CSS 3 + React Router 6 + Lucide icons.

| Route | Page |
|---|---|
| `/` | Home: search bar, marketplace selector, examples, recent searches, categories, how it works |
| `/search?q=&locale=&sort=&brand=` | Results grid with sort, brand filter, skeleton, empty and error states |
| `/product/:locale/:productId` | Product details; carries the originating search in its query string |

Key files: `src/lib/api.ts` (fetch wrapper, typed errors, friendly messages), `src/lib/text.ts` (HTML to safe text), `src/lib/history.ts` (session search history), `src/components/SearchBar.tsx` (accessible combobox with suggestions), `src/pages/*`.

Design notes:
- The URL is the source of truth, so the search query, marketplace, sort and brand filter survive refresh and Back. Results are cached per tab so returning to a search is instant and restores scroll position.
- Catalog HTML is converted to plain text and rendered only as React text nodes (no `dangerouslySetInnerHTML`), so catalog markup cannot execute.
- Only fields present in the data are shown. Missing values are labelled "Not available" or omitted. There are no prices, ratings, stock or sellers because the catalog has none.
- Images: the indexed payload has no image field (the ESCI catalog provides none), so a neutral placeholder is shown.
- Each search asks for the top 24 of 50 retrieved candidates; the UI states "ranked from N retrieved candidates".
- No cart, checkout, payments or authentication, by design.

## Tests

```bash
python -m pytest tests -q          # backend: API (offline, temp Qdrant), features, metrics
cd frontend && npm test            # frontend: Vitest + Testing Library (mocked fetch)
cd frontend && npm run build       # type-check + production build
```

Backend API tests use a tiny temporary Qdrant collection, a stub query encoder and a stub ranker, so they need neither the trained model nor a model download.

Manual check with the real stack: start both servers, search "wireless headphones" in US, open a result, confirm the title/ID/marketplace match, press Back, switch to JP or ES and search again.

## Known limitations

- The Qdrant index may be a **development subset** (e.g. 15,000 products, built with `--limit-per-locale`). Results are not full-catalog retrieval; the site shows a notice when `index_metadata.json` marks the index as a subset.
- No product images, prices, ratings or stock: not in the source data.
- Descriptions are shown as plain text; HTML structure beyond paragraphs and list items is flattened.
- Search results are cached per browser tab and are not refreshed until a new search or reload with changed parameters.
