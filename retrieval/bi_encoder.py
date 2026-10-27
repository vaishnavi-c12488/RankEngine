
"""Dense query and product encoding for RankEngine."""

from __future__ import annotations

from functools import lru_cache

import numpy as np

DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


@lru_cache(maxsize=2)
def load_encoder(model_name: str = DEFAULT_MODEL):
    """Load and cache the sentence-transformer model on demand."""
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(model_name, device="cpu")


def encode_texts(
    texts: list[str],
    model_name: str = DEFAULT_MODEL,
    batch_size: int = 32,
) -> np.ndarray:
    """Encode text into normalized dense vectors."""
    if batch_size < 1:
        raise ValueError("batch_size must be positive")

    normalized_texts = [
        text.strip() if isinstance(text, str) else ""
        for text in texts
    ]

    if not normalized_texts:
        model = load_encoder(model_name)
        return np.empty(
            (0, model.get_sentence_embedding_dimension()),
            dtype=np.float32,
        )

    model = load_encoder(model_name)
    vectors = model.encode(
        normalized_texts,
        batch_size=batch_size,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=len(normalized_texts) > batch_size,
    )
    return np.asarray(vectors, dtype=np.float32)


def encode_query(
    query: str,
    model_name: str = DEFAULT_MODEL,
) -> np.ndarray:
    """Return a single normalized query embedding."""
    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must be a non-empty string")

    return encode_texts([query], model_name=model_name)[0]


def encode_products(
    product_texts: list[str],
    model_name: str = DEFAULT_MODEL,
    batch_size: int = 32,
) -> np.ndarray:
    """Encode product text in batches."""
    return encode_texts(
        product_texts,
        model_name=model_name,
        batch_size=batch_size,
    )
