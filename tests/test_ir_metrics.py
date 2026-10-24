
"""Unit tests for RankEngine information retrieval metrics."""

import math

import pytest

from evaluation.ir_metrics import (
    dcg_at_k,
    evaluate_ranked_query,
    mean_defined,
    ndcg_at_k,
    precision_at_k,
    reciprocal_rank,
    recall_at_k,
    summarize_metrics,
)


def test_perfect_ndcg_is_one():
    assert ndcg_at_k([3, 2, 1], all_relevances=[3, 2, 1], k=3) == pytest.approx(1.0)


def test_ndcg_penalizes_wrong_order():
    assert ndcg_at_k([1, 3], all_relevances=[3, 1], k=2) < 1.0


def test_ndcg_uses_unretrieved_judgments_for_ideal():
    score = ndcg_at_k([3], all_relevances=[3, 2, 1], k=3)
    assert 0.0 < score < 1.0


def test_ndcg_returns_none_when_ideal_is_zero():
    assert ndcg_at_k([0, 0], all_relevances=[0, 0]) is None


def test_linear_dcg():
    assert dcg_at_k([3, 2], k=2, gain="linear") == pytest.approx(
        3 + 2 / math.log2(3)
    )


def test_invalid_gain_raises():
    with pytest.raises(ValueError):
        dcg_at_k([3], gain="unknown")


def test_mrr_exact_only():
    assert reciprocal_rank([2, 1, 3], relevant_threshold=3) == pytest.approx(1 / 3)


def test_mrr_returns_zero_if_none_relevant():
    assert reciprocal_rank([2, 1, 0], relevant_threshold=3) == 0.0


def test_precision_at_five_counts_missing_positions_as_nonrelevant():
    assert precision_at_k([3, 2], k=5, relevant_threshold=3) == pytest.approx(1 / 5)


def test_precision_can_include_substitutes():
    assert precision_at_k([2, 3], k=2, relevant_threshold=2) == 1.0


def test_recall_uses_all_judged_relevant_items():
    assert recall_at_k([3, 0], all_relevances=[3, 3, 0], k=2) == pytest.approx(0.5)


def test_recall_returns_none_when_no_relevant_items():
    assert recall_at_k([0, 0], all_relevances=[0, 0]) is None


def test_metric_k_must_be_positive():
    with pytest.raises(ValueError):
        precision_at_k([3], k=0)


def test_negative_relevance_is_rejected():
    with pytest.raises(ValueError):
        ndcg_at_k([-1, 0])


def test_mean_defined_ignores_none():
    assert mean_defined([0.5, None, 1.0]) == pytest.approx(0.75)


def test_mean_defined_returns_none_if_all_undefined():
    assert mean_defined([None, None]) is None


def test_empty_summary():
    assert summarize_metrics([]) == {}


def test_summary_macro_averages_metrics():
    rows = [
        {"mrr": 1.0, "ndcg@10": 0.5},
        {"mrr": 0.0, "ndcg@10": None},
    ]
    summary = summarize_metrics(rows)
    assert summary["mrr"] == pytest.approx(0.5)
    assert summary["ndcg@10"] == pytest.approx(0.5)


def test_evaluate_ranked_query_returns_expected_metrics():
    result = evaluate_ranked_query(
        ranked_relevances=[3, 0, 2],
        all_relevances=[3, 2, 0],
    )
    assert result["mrr"] == 1.0
    assert result["precision@5"] == pytest.approx(1 / 5)
    assert result["recall@10"] == pytest.approx(1.0)
    assert result["ndcg@10"] is not None


def test_exact_only_threshold():
    assert reciprocal_rank([2, 0], relevant_threshold=3) == 0.0


def test_exact_plus_substitute_threshold():
    assert reciprocal_rank([2, 0], relevant_threshold=2) == 1.0


def test_ndcg_linear_gain_supported():
    assert ndcg_at_k(
        [3, 2],
        all_relevances=[3, 2],
        gain="linear",
    ) == pytest.approx(1.0)


def test_recall_is_bounded():
    result = recall_at_k([3, 2], all_relevances=[3, 2, 0], k=2)
    assert result is not None
    assert 0.0 <= result <= 1.0


def test_precision_is_bounded():
    result = precision_at_k([3, 2, 0], k=3)
    assert 0.0 <= result <= 1.0


def test_empty_ranked_list_has_zero_mrr():
    assert reciprocal_rank([]) == 0.0
