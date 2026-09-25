"""Local, deterministic safeguards for Journey RAG requests and responses.

These guards are intentionally explainable and testable. They complement, rather
than replace, authentication, network controls, and deployment monitoring.
"""

from __future__ import annotations

from collections import defaultdict, deque
from time import monotonic
from typing import Any


class GuardrailViolation(ValueError):
    """A request or response failed a local safety policy."""


_INJECTION_PATTERNS = (
    "ignore previous instructions",
    "ignore all previous instructions",
    "reveal your system prompt",
    "show your system prompt",
    "developer message",
    "system message",
)


def validate_question(question: str, *, max_length: int = 1_000) -> str:
    """Reject empty, oversized, and obvious prompt-injection requests."""
    normalized = question.strip()
    if not normalized:
        raise GuardrailViolation("Provide a non-empty question.")
    if len(normalized) > max_length:
        raise GuardrailViolation("Question exceeds the allowed length.")
    lowered = normalized.lower()
    if any(pattern in lowered for pattern in _INJECTION_PATTERNS):
        raise GuardrailViolation("Request was blocked by the prompt-injection guardrail.")
    return normalized


def validate_citations(citations: list[dict[str, Any]]) -> None:
    """Require citations that identify a retrieved textbook passage."""
    if not citations:
        raise GuardrailViolation("Grounded responses require at least one citation.")
    for citation in citations:
        if not citation.get("problem_id") or citation.get("page") is None:
            raise GuardrailViolation("A response citation is incomplete.")


class SlidingWindowRateLimiter:
    """Small in-memory request limiter for local development, keyed by client ID."""

    def __init__(self, *, limit: int = 20, window_seconds: float = 60.0) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._requests: dict[str, deque[float]] = defaultdict(deque)

    def check(self, client_id: str, *, now: float | None = None) -> None:
        current = monotonic() if now is None else now
        requests = self._requests[client_id]
        while requests and current - requests[0] >= self.window_seconds:
            requests.popleft()
        if len(requests) >= self.limit:
            raise GuardrailViolation("Too many requests. Try again shortly.")
        requests.append(current)
