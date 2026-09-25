"""Structured, grounded learning interactions built on the existing Journey RAG pipeline."""

from __future__ import annotations

import json
from typing import Any, Callable

import ollama
from pydantic import BaseModel, Field


class LearningRequest(BaseModel):
    """A topic the learner wants explained and assessed."""

    question: str = Field(min_length=1, max_length=1_000)
    learning_goal: str | None = Field(default=None, max_length=500)
    quiz_size: int = Field(default=3, ge=1, le=5)


class QuizItem(BaseModel):
    """A learner-facing multiple-choice question without an exposed answer key."""

    question: str
    choices: list[str] = Field(min_length=2, max_length=4)
    source_problem_ids: list[str]


class LearningResponse(BaseModel):
    """A cited explanation and a quiz generated only from its grounded context."""

    explanation: str
    citations: list[dict[str, Any]]
    quiz: list[QuizItem]
    next_action: str


class LearningServiceError(RuntimeError):
    """Raised when a local model cannot return a valid learner-facing quiz."""


def _normalized_question(question: str) -> str:
    normalized = question.strip()
    if not normalized:
        raise ValueError("Provide a non-empty learning question.")
    return normalized


def _quiz_prompt(
    *, explanation: str, citations: list[dict[str, Any]], learning_goal: str | None, quiz_size: int
) -> str:
    source_ids = [str(citation.get("problem_id", "Unknown source")) for citation in citations]
    goal = learning_goal or "Check conceptual understanding."
    return f"""You create learner-facing multiple-choice questions for a MATLAB course.
Use only the grounded explanation and source identifiers below. Do not introduce facts that are not supported.

LEARNING GOAL: {goal}
GROUNDED EXPLANATION:
{explanation}

SOURCE PROBLEM IDS: {source_ids}

Return valid JSON only, with this exact shape:
{{"quiz":[{{"question":"...","choices":["...","...","...","..."],"source_problem_ids":["..."]}}]}}

Create exactly {quiz_size} questions. Each question needs two to four choices. Do not include answers, explanations, grades, or markdown."""


def _parse_quiz(raw_content: str, expected_size: int) -> list[QuizItem]:
    try:
        data = json.loads(raw_content)
        quiz = [QuizItem.model_validate(item) for item in data["quiz"]]
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise LearningServiceError("The local model returned an invalid quiz payload.") from exc

    if len(quiz) != expected_size:
        raise LearningServiceError("The local model returned an unexpected number of quiz questions.")
    return quiz


def generate_quiz(
    *,
    explanation: str,
    citations: list[dict[str, Any]],
    learning_goal: str | None,
    quiz_size: int,
    chat: Callable[..., dict[str, Any]] = ollama.chat,
) -> list[QuizItem]:
    """Create a structured quiz from an already grounded explanation."""
    response = chat(
        model="llama3.2",
        messages=[
            {
                "role": "user",
                "content": _quiz_prompt(
                    explanation=explanation,
                    citations=citations,
                    learning_goal=learning_goal,
                    quiz_size=quiz_size,
                ),
            }
        ],
        format="json",
    )
    try:
        content = response["message"]["content"]
    except (KeyError, TypeError) as exc:
        raise LearningServiceError("The local model did not return quiz content.") from exc
    return _parse_quiz(content, quiz_size)


def create_learning_response(
    request: LearningRequest,
    *,
    answerer: Callable[[str], tuple[str, list[dict[str, Any]]] | tuple[Any, Any]] | None = None,
    quiz_generator: Callable[..., list[QuizItem]] = generate_quiz,
) -> LearningResponse:
    """Reuse Journey's RAG answer, then create a schema-checked learner quiz."""
    question = _normalized_question(request.question)
    if answerer is None:
        from query import ask_journey

        answerer = ask_journey

    explanation, citations = answerer(question)
    quiz = quiz_generator(
        explanation=explanation,
        citations=citations,
        learning_goal=request.learning_goal,
        quiz_size=request.quiz_size,
    )
    return LearningResponse(
        explanation=explanation,
        citations=citations,
        quiz=quiz,
        next_action="Submit quiz answers for evaluation in the next planned phase.",
    )
