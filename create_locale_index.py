
import os

from qdrant_client import QdrantClient, models

collection_name = "rankengine_products"

qdrant_url = os.environ.get("QDRANT_URL", "").strip()
qdrant_api_key = os.environ.get("QDRANT_API_KEY", "").strip()

if not qdrant_url or not qdrant_api_key:
    raise SystemExit(
        "QDRANT_URL and QDRANT_API_KEY must be set in the environment."
    )

client = QdrantClient(
    url=qdrant_url,
    api_key=qdrant_api_key,
    timeout=60,
)

try:
    if not client.collection_exists(collection_name):
        raise SystemExit(
            f"Collection '{collection_name}' was not found. No changes made."
        )

    client.create_payload_index(
        collection_name=collection_name,
        field_name="product_locale",
        field_schema=models.PayloadSchemaType.KEYWORD,
        wait=True,
    )

    print(
        "Success: payload index for 'product_locale' "
        f"created or confirmed on '{collection_name}'."
    )
finally:
    client.close()
