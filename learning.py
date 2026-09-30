"""Structured, grounded learning interactions built on the existing Journey RAG pipeline."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Callable

import ollama
from pydantic import BaseModel, Field

QUIZ_GENERATION_ATTEMPTS = 2


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


class ScoredQuizItem(QuizItem):
    """Internal quiz representation. The answer index must never reach a learner."""

    correct_choice_index: int


class LearningResponse(BaseModel):
    """A cited explanation and a quiz generated only from its grounded context."""

    explanation: str
    citations: list[dict[str, Any]]
    quiz: list[QuizItem]
    next_action: str


@dataclass(frozen=True)
class LearningSessionDraft:
    """A learner-safe response plus an internal server-side answer key."""

    response: LearningResponse
    answer_key: list[int]


class LearningServiceError(RuntimeError):
    """Raised when a local model cannot return a valid learner-facing quiz."""


def _quiz_json_schema(quiz_size: int, *, include_answer_key: bool) -> dict[str, Any]:
    """Constrain Ollama output before applying the Pydantic and semantic checks."""
    properties: dict[str, Any] = {
        "question": {"type": "string", "minLength": 1},
        "choices": {
            "type": "array",
            "minItems": 2,
            "maxItems": 4,
            "items": {"type": "string"},
        },
        "source_problem_ids": {
            "type": "array",
            "minItems": 1,
            "items": {"type": "string"},
        },
    }
    required = ["question", "choices", "source_problem_ids"]
    if include_answer_key:
        properties["correct_choice_index"] = {"type": "integer", "minimum": 0}
        required.append("correct_choice_index")
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "quiz": {
                "type": "array",
                "minItems": quiz_size,
                "maxItems": quiz_size,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": properties,
                    "required": required,
                },
            }
        },
        "required": ["quiz"],
    }


def _normalized_question(question: str) -> str:
    normalized = question.strip()
    if not normalized:
        raise ValueError("Provide a non-empty learning question.")
    return normalized


def _quiz_prompt(
    *,
    explanation: str,
    citations: list[dict[str, Any]],
    learning_goal: str | None,
    quiz_size: int,
    include_answer_key: bool = False,
) -> str:
    source_ids = [str(citation.get("problem_id", "Unknown source")) for citation in citations]
    goal = learning_goal or "Check conceptual understanding."
    answer_instruction = (
        'Add "correct_choice_index" to every quiz item. It must be a zero-based index into choices. '
        if include_answer_key
        else ""
    )
    ending_instruction = (
        "Do not include explanations, grades, or markdown."
        if include_answer_key
        else "Do not include answers, explanations, grades, or markdown."
    )
    item_shape = (
        '{"question":"...","choices":["...","..."],"source_problem_ids":["..."],"correct_choice_index":0}'
        if include_answer_key
        else '{"question":"...","choices":["...","..."],"source_problem_ids":["..."]}'
    )
    return f"""You create learner-facing multiple-choice questions for a MATLAB course.
Use only the grounded explanation and source identifiers below. Do not introduce facts that are not supported.

LEARNING GOAL: {goal}
GROUNDED EXPLANATION:
{explanation}

SOURCE PROBLEM IDS: {source_ids}

Return valid JSON only, with this exact shape:
{{"quiz":[{item_shape}]}}

{answer_instruction}Create exactly {quiz_size} questions. Each question needs two to four choices. {ending_instruction}"""


def _parse_quiz(raw_content: str, expected_size: int) -> list[QuizItem]:
    try:
        data = json.loads(raw_content)
        quiz = [QuizItem.model_validate(item) for item in data["quiz"]]
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise LearningServiceError("The local model returned an invalid quiz payload.") from exc

    if len(quiz) != expected_size:
        raise LearningServiceError("The local model returned an unexpected number of quiz questions.")
    return quiz


def _parse_scored_quiz(raw_content: str, expected_size: int) -> list[ScoredQuizItem]:
    try:
        data = json.loads(raw_content)
        quiz = [ScoredQuizItem.model_validate(item) for item in data["quiz"]]
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise LearningServiceError("The local model returned an invalid scored quiz payload.") from exc

    if len(quiz) != expected_size:
        raise LearningServiceError("The local model returned an unexpected number of quiz questions.")
    for item in quiz:
        if item.correct_choice_index < 0 or item.correct_choice_index >= len(item.choices):
            raise LearningServiceError("The local model returned an invalid quiz answer index.")
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
    prompt = _quiz_prompt(
        explanation=explanation,
        citations=citations,
        learning_goal=learning_goal,
        quiz_size=quiz_size,
    )
    last_error: LearningServiceError | None = None
    for attempt in range(QUIZ_GENERATION_ATTEMPTS):
        messages = [{"role": "user", "content": prompt}]
        if attempt:
            messages.append({
                "role": "user",
                "content": "The previous response failed validation. Return only valid JSON in the exact requested shape.",
            })
        response = chat(
            model=os.getenv("JOURNEY_LLM_MODEL", "llama3.2"),
            messages=messages,
            format=_quiz_json_schema(quiz_size, include_answer_key=False),
        )
        try:
            content = response["message"]["content"]
            return _parse_quiz(content, quiz_size)
        except (KeyError, TypeError) as exc:
            last_error = LearningServiceError("The local model did not return quiz content.")
            last_error.__cause__ = exc
        except LearningServiceError as exc:
            last_error = exc
    assert last_error is not None
    raise last_error


def generate_scored_quiz(
    *,
    explanation: str,
    citations: list[dict[str, Any]],
    learning_goal: str | None,
    quiz_size: int,
    chat: Callable[..., dict[str, Any]] = ollama.chat,
) -> list[ScoredQuizItem]:
    """Generate a quiz whose answer key is retained by the server only."""
    prompt = _quiz_prompt(
        explanation=explanation,
        citations=citations,
        learning_goal=learning_goal,
        quiz_size=quiz_size,
        include_answer_key=True,
    )
    last_error: LearningServiceError | None = None
    for attempt in range(QUIZ_GENERATION_ATTEMPTS):
        messages = [{"role": "user", "content": prompt}]
        if attempt:
            messages.append({
                "role": "user",
                "content": "The previous response failed validation. Return only valid JSON in the exact requested shape, including every correct_choice_index.",
            })
        response = chat(
            model=os.getenv("JOURNEY_LLM_MODEL", "llama3.2"),
            messages=messages,
            format=_quiz_json_schema(quiz_size, include_answer_key=True),
        )
        try:
            content = response["message"]["content"]
            return _parse_scored_quiz(content, quiz_size)
        except (KeyError, TypeError) as exc:
            last_error = LearningServiceError("The local model did not return scored quiz content.")
            last_error.__cause__ = exc
        except LearningServiceError as exc:
            last_error = exc
    assert last_error is not None
    raise last_error


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
        next_action="Review the cited explanation, then complete the quiz.",
    )


def create_learning_session(
    request: LearningRequest,
    *,
    answerer: Callable[[str], tuple[str, list[dict[str, Any]]] | tuple[Any, Any]] | None = None,
    quiz_generator: Callable[..., list[ScoredQuizItem]] = generate_scored_quiz,
) -> LearningSessionDraft:
    """Create a real local learning session without exposing its answer key."""
    question = _normalized_question(request.question)
    if answerer is None:
        from query import ask_journey

        answerer = ask_journey

    explanation, citations = answerer(question)
    scored_quiz = quiz_generator(
        explanation=explanation,
        citations=citations,
        learning_goal=request.learning_goal,
        quiz_size=request.quiz_size,
    )
    public_quiz = [
        QuizItem(
            question=item.question,
            choices=item.choices,
            source_problem_ids=item.source_problem_ids,
        )
        for item in scored_quiz
    ]
    return LearningSessionDraft(
        response=LearningResponse(
            explanation=explanation,
            citations=citations,
            quiz=public_quiz,
            next_action="Answer the quiz to receive a personalized next step.",
        ),
        answer_key=[item.correct_choice_index for item in scored_quiz],
    )
