"""Local BM25 and Reciprocal Rank Fusion utilities for retrieval experiments."""

from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any, Iterable


def stable_chunk_id(chunk: dict[str, Any], position: int) -> str:
    """Produce a stable source identifier for citations and evaluation labels."""
    return f"{chunk['source_pdf']}:{chunk['page_number']}:{chunk['problem_id']}:{position}"


def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9_]+", text.lower())


@dataclass(frozen=True)
class LexicalDocument:
    chunk_id: str
    text: str
    metadata: dict[str, Any]


class BM25Index:
    """Small dependency-free BM25 index for local textbook experiments."""

    def __init__(self, documents: Iterable[LexicalDocument], *, k1: float = 1.5, b: float = 0.75):
        self.documents = list(documents)
        self.k1 = k1
        self.b = b
        self.term_frequencies = [Counter(tokenize(document.text)) for document in self.documents]
        self.lengths = [sum(freq.values()) for freq in self.term_frequencies]
        self.average_length = sum(self.lengths) / len(self.lengths) if self.lengths else 0.0
        self.document_frequency: Counter[str] = Counter()
        for frequencies in self.term_frequencies:
            self.document_frequency.update(frequencies.keys())

    def search(self, query: str, top_k: int = 10) -> list[tuple[LexicalDocument, float]]:
        if top_k < 1:
            raise ValueError("top_k must be at least 1.")
        terms = tokenize(query)
        total_documents = len(self.documents)
        if not terms or not total_documents:
            return []

        ranked: list[tuple[LexicalDocument, float]] = []
        for document, frequencies, length in zip(self.documents, self.term_frequencies, self.lengths, strict=True):
            score = 0.0
            for term in terms:
                frequency = frequencies.get(term, 0)
                if not frequency:
                    continue
                idf = math.log(1 + (total_documents - self.document_frequency[term] + 0.5) / (self.document_frequency[term] + 0.5))
                denominator = frequency + self.k1 * (1 - self.b + self.b * length / self.average_length)
                score += idf * (frequency * (self.k1 + 1) / denominator)
            if score:
                ranked.append((document, score))
        return sorted(ranked, key=lambda item: item[1], reverse=True)[:top_k]


def reciprocal_rank_fusion(rankings: Iterable[Iterable[str]], *, k: int = 60, top_k: int = 10) -> list[str]:
    """Combine ranked identifiers without comparing incompatible score scales."""
    if k < 1 or top_k < 1:
        raise ValueError("k and top_k must be at least 1.")
    scores: defaultdict[str, float] = defaultdict(float)
    for ranking in rankings:
        for rank, item_id in enumerate(ranking, start=1):
            scores[item_id] += 1 / (k + rank)
    return [item_id for item_id, _ in sorted(scores.items(), key=lambda item: (-item[1], item[0]))[:top_k]]
