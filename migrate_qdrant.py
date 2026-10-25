
import os
from pathlib import Path

from qdrant_client import QdrantClient

SOURCE_PATH = str(Path("data/index/qdrant").resolve())
COLLECTION = "rankengine_products"
BATCH_SIZE = 128


def main():
    cloud_url = os.getenv("QDRANT_CLOUD_URL", "").strip()
    cloud_api_key = os.getenv("QDRANT_CLOUD_API_KEY", "").strip()

    if not cloud_url or not cloud_api_key:
        raise RuntimeError(
            "Set QDRANT_CLOUD_URL and QDRANT_CLOUD_API_KEY "
            "before running the migration."
        )

    source = QdrantClient(path=SOURCE_PATH)
    destination = QdrantClient(
        url=cloud_url,
        api_key=cloud_api_key,
        timeout=60,
    )

    try:
        source_info = source.get_collection(COLLECTION)
        source_count = source.count(
            collection_name=COLLECTION,
            exact=True,
        ).count

        print(f"Source points: {source_count}")

        if source_count == 0:
            raise RuntimeError("Source collection is empty. Stopping.")

        if source_info.config.params.vectors is None:
            raise RuntimeError(
                "Source uses an unsupported vector configuration."
            )

        if destination.collection_exists(COLLECTION):
            destination_count = destination.count(
                collection_name=COLLECTION,
                exact=True,
            ).count

            if destination_count != 0:
                raise RuntimeError(
                    f"Destination already has {destination_count} points. "
                    "Stopping to avoid overwriting existing data."
                )

            raise RuntimeError(
                "Destination collection exists but is empty. "
                "Check its configuration before retrying."
            )

        destination.create_collection(
            collection_name=COLLECTION,
            vectors_config=source_info.config.params.vectors,
            on_disk_payload=source_info.config.params.on_disk_payload,
        )

        offset = None
        copied = 0

        while True:
            points, next_offset = source.scroll(
                collection_name=COLLECTION,
                offset=offset,
                limit=BATCH_SIZE,
                with_payload=True,
                with_vectors=True,
            )

            if not points:
                break

            destination.upload_points(
                collection_name=COLLECTION,
                points=points,
                batch_size=BATCH_SIZE,
                parallel=1,
                max_retries=3,
                wait=True,
            )

            copied += len(points)
            print(f"Copied {copied}/{source_count} points")

            if next_offset is None:
                break

            offset = next_offset

        destination_count = destination.count(
            collection_name=COLLECTION,
            exact=True,
        ).count

        print(f"\nSource count:      {source_count}")
        print(f"Destination count: {destination_count}")

        if destination_count != source_count:
            raise RuntimeError(
                "Migration verification failed: point counts differ."
            )

        print("Migration count verification passed.")

    finally:
        source.close()
        destination.close()


if __name__ == "__main__":
    main()
