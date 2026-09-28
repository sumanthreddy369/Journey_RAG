"""Offline retrieval evaluation for versioned, human-labeled Journey test cases."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from retrieval_metrics import mean_reciprocal_rank, ndcg_at_k


@dataclass(frozen=True)
class RetrievalCase:
    question: str
    relevant_chunk_ids: set[str]


def load_cases(path: str | Path) -> list[RetrievalCase]:
    raw_cases = json.loads(Path(path).read_text(encoding="utf-8"))
    return [RetrievalCase(question=item["question"], relevant_chunk_ids=set(item["relevant_chunk_ids"])) for item in raw_cases]


def recall_at_k(ranked_ids: list[str], relevant_ids: set[str], k: int) -> float:
    if k < 1:
        raise ValueError("k must be at least 1.")
    return len(set(ranked_ids[:k]) & relevant_ids) / len(relevant_ids) if relevant_ids else 0.0


def score_rankings(rankings: list[list[str]], cases: list[RetrievalCase], k: int = 5) -> dict[str, float]:
    if len(rankings) != len(cases) or not cases:
        raise ValueError("Provide one non-empty set of rankings for every evaluation case.")
    relevance = [case.relevant_chunk_ids for case in cases]
    return {
        f"recall_at_{k}": sum(recall_at_k(ranking, expected, k) for ranking, expected in zip(rankings, relevance, strict=True)) / len(cases),
        "mrr": mean_reciprocal_rank(rankings, relevance),
        f"ndcg_at_{k}": sum(ndcg_at_k(ranking, expected, k) for ranking, expected in zip(rankings, relevance, strict=True)) / len(cases),
    }
