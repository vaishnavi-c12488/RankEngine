
"""Tests for RankEngine feature engineering."""

import pandas as pd
import pytest

from data.feature_engineering import build_features, jaccard_similarity, token_overlap
from data.tokenization import tokenize


def test_japanese_tokenizer_uses_bigrams():
    assert tokenize("ノートパソコン") == [
        "ノー", "ート", "トパ", "パソ", "ソコ", "コン"
    ]


def test_full_width_normalization():
    assert tokenize("ＡＢＣ 15") == ["abc", "15"]


def test_english_overlap():
    assert token_overlap("wireless headphones", "wireless headphones case") == 1.0


def test_jaccard_similarity():
    assert jaccard_similarity("wireless headphones", "wireless case") == pytest.approx(1 / 3)


def test_empty_query_returns_zero():
    assert token_overlap("", "wireless headphones") == 0.0
    assert jaccard_similarity("", "wireless headphones") == 0.0


def test_features_are_numeric_and_exclude_labels():
    df = pd.DataFrame({
        "query": ["ノートパソコン", "wireless headphones"],
        "product_title": ["ノートパソコン用ケース", "wireless headphones case"],
        "product_description": ["ケース", "Bluetooth audio"],
        "product_bullet_point": ["軽量", "comfortable fit"],
        "product_brand": ["Brand A", ""],
        "product_color": ["Black", None],
        "esci_label": ["E", "I"],
        "relevance": [3, 0],
    })

    features = build_features(df)

    assert len(features) == 2
    assert "esci_label" not in features.columns
    assert "relevance" not in features.columns
    assert all(pd.api.types.is_numeric_dtype(dtype) for dtype in features.dtypes)
    assert features.loc[0, "query_title_overlap"] > 0
    assert features.loc[1, "query_title_overlap"] == 1.0


def test_missing_required_columns_raises():
    with pytest.raises(ValueError, match="Missing required columns"):
        build_features(pd.DataFrame({"query": ["headphones"]}))
