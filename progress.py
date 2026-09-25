"""Local-only quiz evaluation and conditional learning routing primitives.

This module intentionally has no database or identity-provider integration. It is
the deterministic core used before any real learner records are introduced.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class QuizSubmission(BaseModel):
    """A local synthetic learner's selected choice indexes."""

    selected_choice_indexes: list[int] = Field(min_length=1, max_length=5)


class QuizEvaluation(BaseModel):
    total_questions: int
    correct_answers: int
    score_percent: int
    route: str
    next_action: str


def evaluate_submission(submission: QuizSubmission, answer_key: list[int]) -> QuizEvaluation:
    """Score a local quiz and select the next teaching action deterministically."""
    if len(submission.selected_choice_indexes) != len(answer_key):
        raise ValueError("The submitted answer count must match the quiz length.")
    if not answer_key:
        raise ValueError("A quiz needs at least one answer key entry.")

    correct = sum(
        selected == expected
        for selected, expected in zip(submission.selected_choice_indexes, answer_key, strict=True)
    )
    score_percent = round((correct / len(answer_key)) * 100)
    if score_percent < 60:
        route = "reteach"
        next_action = "Review the grounded explanation, then try a simpler follow-up quiz."
    elif score_percent < 85:
        route = "practice"
        next_action = "Practice a similar problem with another cited quiz."
    else:
        route = "advance"
        next_action = "Try a more challenging topic or application question."
    return QuizEvaluation(
        total_questions=len(answer_key),
        correct_answers=correct,
        score_percent=score_percent,
        route=route,
        next_action=next_action,
    )
