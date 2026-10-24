
"""Information retrieval metrics for RankEngine.

NDCG uses graded relevance by default with exponential gains.
MRR, Precision@K and Recall@K use a configurable binary threshold.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence


def _validate_k(k: int) -> None:
    if not isinstance(k, int) or isinstance(k, bool) or k < 1:
        raise ValueError("k must be a positive integer")


def _relevance_value(value: object) -> float:
    """Convert a relevance value to a finite non-negative float."""
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid relevance value: {value!r}") from exc

    if not math.isfinite(result) or result < 0:
        raise ValueError("Relevance values must be finite and non-negative")

    return result


def dcg_at_k(
    relevances: Sequence[float],
    k: int = 10,
    gain: str = "exponential",
) -> float:
    """Compute DCG@K from relevance values in ranked order."""
    _validate_k(k)

    if gain not in {"exponential", "linear"}:
        raise ValueError("gain must be 'exponential' or 'linear'")

    total = 0.0

    for rank, raw_relevance in enumerate(relevances[:k], start=1):
        relevance = _relevance_value(raw_relevance)
        gain_value = (
            (2**relevance - 1)
            if gain == "exponential"
            else relevance
        )
        total += gain_value / math.log2(rank + 1)

    return total


def ndcg_at_k(
    ranked_relevances: Sequence[float],
    all_relevances: Sequence[float] | None = None,
    k: int = 10,
    gain: str = "exponential",
) -> float | None:
    """Compute NDCG@K.

    If all_relevances is supplied, it defines the ideal ranking. This lets
    evaluation account for relevant judged products not retrieved by a system.
    Returns None if the ideal DCG is zero.
    """
    _validate_k(k)

    ideal_source = (
        all_relevances
        if all_relevances is not None
        else ranked_relevances
    )

    ideal_relevances = sorted(
        (_relevance_value(value) for value in ideal_source),
        reverse=True,
    )
    ideal_dcg = dcg_at_k(ideal_relevances, k=k, gain=gain)

    if ideal_dcg == 0:
        return None

    actual_dcg = dcg_at_k(ranked_relevances, k=k, gain=gain)
    return actual_dcg / ideal_dcg


def reciprocal_rank(
    ranked_relevances: Sequence[float],
    relevant_threshold: float = 3,
) -> float:
    """Return reciprocal rank of the first item meeting the threshold."""
    threshold = _relevance_value(relevant_threshold)

    for rank, raw_relevance in enumerate(ranked_relevances, start=1):
        if _relevance_value(raw_relevance) >= threshold:
            return 1.0 / rank

    return 0.0


def precision_at_k(
    ranked_relevances: Sequence[float],
    k: int = 5,
    relevant_threshold: float = 3,
) -> float:
    """Compute Precision@K; missing positions count as non-relevant."""
    _validate_k(k)
    threshold = _relevance_value(relevant_threshold)

    relevant_count = sum(
        _relevance_value(value) >= threshold
        for value in ranked_relevances[:k]
    )

    return relevant_count / k


def recall_at_k(
    ranked_relevances: Sequence[float],
    all_relevances: Sequence[float],
    k: int = 10,
    relevant_threshold: float = 3,
) -> float | None:
    """Compute Recall@K against all judged products for the query.

    Returns None when no judged product meets the relevance threshold.
    """
    _validate_k(k)
    threshold = _relevance_value(relevant_threshold)

    total_relevant = sum(
        _relevance_value(value) >= threshold
        for value in all_relevances
    )

    if total_relevant == 0:
        return None

    retrieved_relevant = sum(
        _relevance_value(value) >= threshold
        for value in ranked_relevances[:k]
    )

    return retrieved_relevant / total_relevant


def evaluate_ranked_query(
    ranked_relevances: Sequence[float],
    all_relevances: Sequence[float],
    relevant_threshold: float = 3,
    k_ndcg: int = 10,
    k_precision: int = 5,
    k_recall: int = 10,
    gain: str = "exponential",
) -> dict[str, float | None]:
    """Calculate the main RankEngine metrics for one query."""
    return {
        f"ndcg@{k_ndcg}": ndcg_at_k(
            ranked_relevances,
            all_relevances=all_relevances,
            k=k_ndcg,
            gain=gain,
        ),
        "mrr": reciprocal_rank(
            ranked_relevances,
            relevant_threshold=relevant_threshold,
        ),
        f"precision@{k_precision}": precision_at_k(
            ranked_relevances,
            k=k_precision,
            relevant_threshold=relevant_threshold,
        ),
        f"recall@{k_recall}": recall_at_k(
            ranked_relevances,
            all_relevances=all_relevances,
            k=k_recall,
            relevant_threshold=relevant_threshold,
        ),
    }


def mean_defined(values: Sequence[float | None]) -> float | None:
    """Average defined metric values, excluding None values."""
    defined = [float(value) for value in values if value is not None]

    if not defined:
        return None

    return sum(defined) / len(defined)


def summarize_metrics(
    per_query: Sequence[Mapping[str, float | None]],
) -> dict[str, float | None]:
    """Macro-average each metric across queries with defined values."""
    if not per_query:
        return {}

    metric_names = per_query[0].keys()

    return {
        name: mean_defined([row.get(name) for row in per_query])
        for name in metric_names
    }
