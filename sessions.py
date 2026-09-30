"""In-memory quiz sessions for the local development workflow.

Answer keys remain server-side. Only anonymous results reach the optional recorder.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Callable
from uuid import uuid4

from progress import QuizEvaluation, QuizSubmission, evaluate_submission


@dataclass
class QuizSession:
    session_id: str
    answer_key: tuple[int, ...]
    topic: str | None = None
    result: QuizEvaluation | None = None
    timestamp: datetime | None = None
    saved: bool = False


class LocalQuizSessionStore:
    """Process-local answer keys and completed attempts for a single local worker."""

    def __init__(self) -> None:
        self._sessions: dict[str, QuizSession] = {}
        self._lock = Lock()
        self._last_timestamp = datetime.min.replace(tzinfo=timezone.utc)

    def create(self, answer_key: list[int], topic: str | None = None) -> str:
        if not answer_key:
            raise ValueError("A quiz session needs at least one answer key entry.")
        session_id = str(uuid4())
        self._sessions[session_id] = QuizSession(session_id=session_id, answer_key=tuple(answer_key), topic=topic)
        return session_id

    def evaluate(self, session_id: str, submission: QuizSubmission) -> QuizEvaluation:
        session = self._sessions.get(session_id)
        if session is None:
            raise KeyError("Quiz session was not found. Create a new learning session.")
        return evaluate_submission(submission, list(session.answer_key))

    def complete(self, session_id: str, submission: QuizSubmission,
                 recorder: Callable[[str, QuizEvaluation, datetime], bool]) -> tuple[QuizEvaluation, bool]:
        """Freeze the first valid attempt and allow failed saves to be retried."""
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None or session.topic is None:
                raise KeyError("Learning session was not found. Create a new learning session.")
            if session.result is None:
                session.result = self.evaluate(session_id, submission)
                session.timestamp = max(datetime.now(timezone.utc), self._last_timestamp + timedelta(microseconds=1))
                self._last_timestamp = session.timestamp
            if not session.saved:
                assert session.timestamp is not None
                session.saved = recorder(session.topic, session.result, session.timestamp)
            return session.result, session.saved
