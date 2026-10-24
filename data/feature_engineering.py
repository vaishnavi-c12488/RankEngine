
"""Create query-product interaction features for RankEngine."""

from __future__ import annotations

from collections.abc import Mapping

import pandas as pd

from data.tokenization import normalize, tokenize


def token_overlap(query: object, document: object) -> float:
    """Return the fraction of unique query tokens found in the document."""
    query_tokens = set(tokenize(query))

    if not query_tokens:
        return 0.0

    document_tokens = set(tokenize(document))
    return len(query_tokens & document_tokens) / len(query_tokens)


def jaccard_similarity(query: object, document: object) -> float:
    """Calculate Jaccard similarity between query and document tokens."""
    query_tokens = set(tokenize(query))
    document_tokens = set(tokenize(document))
    union = query_tokens | document_tokens

    if not union:
        return 0.0

    return len(query_tokens & document_tokens) / len(union)


def build_features(
    df: pd.DataFrame,
    config: Mapping[str, object] | None = None,
) -> pd.DataFrame:
    """Build numeric query-product features without using relevance labels."""
    required = {"query", "product_title"}
    missing = required - set(df.columns)

    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    features = pd.DataFrame(index=df.index)

    query_text = df["query"].fillna("").astype(str)
    title_text = df["product_title"].fillna("").astype(str)

    def get_text_column(column: str) -> pd.Series:
        if column in df.columns:
            return df[column].fillna("").astype(str)
        return pd.Series("", index=df.index, dtype=str)

    description = get_text_column("product_description")
    bullets = get_text_column("product_bullet_point")

    full_text = title_text + " " + description + " " + bullets

    query_tokens = [tokenize(text) for text in query_text]
    title_tokens = [tokenize(text) for text in title_text]
    full_text_tokens = [tokenize(text) for text in full_text]

    query_sets = [set(tokens) for tokens in query_tokens]
    title_sets = [set(tokens) for tokens in title_tokens]
    full_text_sets = [set(tokens) for tokens in full_text_tokens]

    features["query_token_count"] = [len(tokens) for tokens in query_tokens]
    features["title_token_count"] = [len(tokens) for tokens in title_tokens]

    title_overlap = []
    title_jaccard = []
    full_overlap = []

    for q_set, t_set, full_set in zip(
        query_sets,
        title_sets,
        full_text_sets,
    ):
        if not q_set:
            title_overlap.append(0.0)
            title_jaccard.append(0.0)
            full_overlap.append(0.0)
            continue

        title_intersection = len(q_set & t_set)
        full_intersection = len(q_set & full_set)
        title_union = len(q_set | t_set)

        title_overlap.append(title_intersection / len(q_set))
        title_jaccard.append(
            title_intersection / title_union if title_union else 0.0
        )
        full_overlap.append(full_intersection / len(q_set))

    features["query_title_overlap"] = title_overlap
    features["query_title_jaccard"] = title_jaccard
    features["query_full_text_overlap"] = full_overlap

    features["title_contains_query"] = [
        int(
            bool(normalize(query).strip())
            and normalize(query) in normalize(title)
        )
        for query, title in zip(query_text, title_text)
    ]

    for column in ["product_brand", "product_color"]:
        if column in df.columns:
            features[f"{column}_present"] = (
                df[column]
                .fillna("")
                .astype(str)
                .str.strip()
                .ne("")
                .astype(int)
            )

    return features.fillna(0.0).astype(float)
