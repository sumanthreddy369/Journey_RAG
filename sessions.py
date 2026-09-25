"""In-memory quiz sessions for the local development workflow.

Answer keys remain server-side. This deliberately does not persist learner data.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from progress import QuizEvaluation, QuizSubmission, evaluate_submission


@dataclass(frozen=True)
class QuizSession:
    session_id: str
    answer_key: tuple[int, ...]


class LocalQuizSessionStore:
    """Process-local session storage intended only for synthetic development data."""

    def __init__(self) -> None:
        self._sessions: dict[str, QuizSession] = {}

    def create(self, answer_key: list[int]) -> str:
        if not answer_key:
            raise ValueError("A quiz session needs at least one answer key entry.")
        session_id = str(uuid4())
        self._sessions[session_id] = QuizSession(session_id=session_id, answer_key=tuple(answer_key))
        return session_id

    def evaluate(self, session_id: str, submission: QuizSubmission) -> QuizEvaluation:
        session = self._sessions.get(session_id)
        if session is None:
            raise KeyError("Quiz session was not found. Create a new learning session.")
        return evaluate_submission(submission, list(session.answer_key))
