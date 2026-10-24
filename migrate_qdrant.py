
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

SOURCE_PATH = "data/index/qdrant"
DESTINATION_URL = "http://localhost:6333"
COLLECTION = "rankengine_products"
BATCH_SIZE = 128


def main():
    source = QdrantClient(path=SOURCE_PATH)
    destination = QdrantClient(url=DESTINATION_URL)

    try:
        source_count = source.count(
            collection_name=COLLECTION,
            exact=True,
        ).count

        print(f"Source points: {source_count}")

        existing = [
            item.name for item in destination.get_collections().collections
        ]

        if COLLECTION in existing:
            destination_count = destination.count(
                collection_name=COLLECTION,
                exact=True,
            ).count

            if destination_count != 0:
                raise RuntimeError(
                    f"Destination collection already has {destination_count} "
                    "points. Stopping to avoid overwriting existing data."
                )
        else:
            destination.create_collection(
                collection_name=COLLECTION,
                vectors_config=VectorParams(
                    size=384,
                    distance=Distance.COSINE,
                ),
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
            )

            copied += len(points)
            print(f"Processed {copied}/{source_count} points")

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
                "Migration verification failed: point counts do not match."
            )

        print("Migration count verification passed.")

    finally:
        source.close()
        destination.close()


if __name__ == "__main__":
    main()
