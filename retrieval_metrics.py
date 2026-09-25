"""Offline ranking metrics for evaluating Journey RAG retrieval changes."""

from __future__ import annotations

from math import log2


def reciprocal_rank(ranked_ids: list[str], relevant_ids: set[str]) -> float:
    """Return reciprocal rank of the first relevant result, or zero when absent."""
    for position, result_id in enumerate(ranked_ids, start=1):
        if result_id in relevant_ids:
            return 1 / position
    return 0.0


def mean_reciprocal_rank(rankings: list[list[str]], relevance: list[set[str]]) -> float:
    """Average reciprocal rank across a fixed evaluation set."""
    if len(rankings) != len(relevance):
        raise ValueError("Each ranking needs a matching relevance set.")
    if not rankings:
        raise ValueError("Provide at least one ranking.")
    return sum(reciprocal_rank(ranking, expected) for ranking, expected in zip(rankings, relevance, strict=True)) / len(rankings)


def ndcg_at_k(ranked_ids: list[str], relevant_ids: set[str], k: int) -> float:
    """Return binary-relevance normalized discounted cumulative gain at k."""
    if k < 1:
        raise ValueError("k must be at least 1.")
    actual = sum(
        1 / log2(position + 1)
        for position, result_id in enumerate(ranked_ids[:k], start=1)
        if result_id in relevant_ids
    )
    ideal_count = min(len(relevant_ids), k)
    ideal = sum(1 / log2(position + 1) for position in range(1, ideal_count + 1))
    return actual / ideal if ideal else 0.0
