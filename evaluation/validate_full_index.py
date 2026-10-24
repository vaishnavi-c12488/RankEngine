import json
from pathlib import Path
from qdrant_client import QdrantClient

root = Path.cwd() / "data" / "index" / "qdrant_full"
client = QdrantClient(path=str(root))

try:
    info = client.get_collection("rankengine_products")
    metadata = json.loads((root / "index_metadata.json").read_text(encoding="utf-8"))
    print("Point count:", info.points_count)
    print("Vector size:", info.config.params.vectors.size)
    print("Metadata:", json.dumps(metadata, indent=2))
finally:
    client.close()
