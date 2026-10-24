
"""Feature engineering for RankEngine's learning-to-rank model."""

from __future__ import annotations

import re
import unicodedata

import numpy as np
import pandas as pd

from data.tokenization import normalize, tokenize

TEXT_COLUMNS = [
    "query",
    "product_title",
    "product_description",
    "product_bullet_point",
    "product_brand",
    "product_color",
]

FEATURE_COLUMNS = [
    "query_token_count",
    "title_token_count",
    "query_title_overlap",
    "query_title_jaccard",
    "query_full_text_overlap",
    "title_contains_query",
    "product_brand_present",
    "product_color_present",
    "title_length",
    "description_length",
    "bullet_point_length",
]


def build_ltr_features(frame: pd.DataFrame) -> pd.DataFrame:
    """Build numeric ranking features without using relevance labels."""
    if not isinstance(frame, pd.DataFrame):
        raise TypeError("frame must be a pandas DataFrame")

    if "query" not in frame.columns:
        raise ValueError("Missing required column: query")

    if "product_title" not in frame.columns:
        raise ValueError("Missing required column: product_title")

    data = frame.copy()

    for column in TEXT_COLUMNS:
        if column not in data.columns:
            data[column] = ""
        data[column] = data[column].fillna("").astype(str)

    queries = data["query"].map(normalize)
    titles = data["product_title"].map(normalize)

    full_text = (
        data["product_title"]
        + " "
        + data["product_description"]
        + " "
        + data["product_bullet_point"]
        + " "
        + data["product_brand"]
        + " "
        + data["product_color"]
    ).map(normalize)

    query_tokens = [set(tokenize(value)) for value in queries]
    title_tokens = [set(tokenize(value)) for value in titles]
    full_tokens = [set(tokenize(value)) for value in full_text]

    query_counts = np.asarray(
        [len(tokens) for tokens in query_tokens], dtype=np.float32
    )
    title_counts = np.asarray(
        [len(tokens) for tokens in title_tokens], dtype=np.float32
    )

    title_overlap = np.asarray(
        [
            len(q & t) / max(len(q), 1)
            for q, t in zip(query_tokens, title_tokens)
        ],
        dtype=np.float32,
    )

    title_jaccard = np.asarray(
        [
            len(q & t) / max(len(q | t), 1)
            for q, t in zip(query_tokens, title_tokens)
        ],
        dtype=np.float32,
    )

    full_overlap = np.asarray(
        [
            len(q & f) / max(len(q), 1)
            for q, f in zip(query_tokens, full_tokens)
        ],
        dtype=np.float32,
    )

    features = pd.DataFrame(index=data.index)
    features["query_token_count"] = query_counts
    features["title_token_count"] = title_counts
    features["query_title_overlap"] = title_overlap
    features["query_title_jaccard"] = title_jaccard
    features["query_full_text_overlap"] = full_overlap

    # Exact normalized substring signal; no relevance labels are consulted.
    features["title_contains_query"] = np.asarray(
        [
            float(bool(q) and q in title)
            for q, title in zip(queries, titles)
        ],
        dtype=np.float32,
    )

    features["product_brand_present"] = (
        data["product_brand"].str.strip().ne("").astype(np.float32)
    )
    features["product_color_present"] = (
        data["product_color"].str.strip().ne("").astype(np.float32)
    )

    features["title_length"] = (
        data["product_title"].str.len().astype(np.float32)
    )
    features["description_length"] = (
        data["product_description"].str.len().astype(np.float32)
    )
    features["bullet_point_length"] = (
        data["product_bullet_point"].str.len().astype(np.float32)
    )

    features = features.replace([np.inf, -np.inf], np.nan).fillna(0.0)
    return features[FEATURE_COLUMNS].astype(np.float32)
