"""Conservative query rewriting; it never replaces the learner's original question."""

from __future__ import annotations


def rewrite_query(question: str) -> str:
    """Normalize whitespace for a deterministic baseline before LLM rewriting is evaluated."""
    return " ".join(question.split())
