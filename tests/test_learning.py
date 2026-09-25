import json

import pytest

from learning import LearningRequest, LearningServiceError, QuizItem, create_learning_response, generate_quiz


def test_create_learning_response_reuses_cited_answer_and_returns_structured_quiz():
    request = LearningRequest(question="Explain scalars", learning_goal="Understand scalar values", quiz_size=1)

    def fake_answerer(question):
        assert question == "Explain scalars"
        return "A scalar has one value.", [{"problem_id": "Problem 3-A.1", "page": 7}]

    def fake_quiz_generator(**kwargs):
        assert kwargs["explanation"] == "A scalar has one value."
        assert kwargs["quiz_size"] == 1
        return [
            QuizItem(
                question="Which value is a scalar?",
                choices=["5", "[1 2]"],
                source_problem_ids=["Problem 3-A.1"],
            )
        ]

    response = create_learning_response(request, answerer=fake_answerer, quiz_generator=fake_quiz_generator)

    assert response.explanation == "A scalar has one value."
    assert response.citations[0]["problem_id"] == "Problem 3-A.1"
    assert response.quiz[0].choices == ["5", "[1 2]"]


def test_generate_quiz_parses_json_model_response():
    payload = {
        "quiz": [
            {
                "question": "Which expression converts degrees to radians?",
                "choices": ["degrees*pi/180", "degrees*180/pi"],
                "source_problem_ids": ["Problem 4-A.11"],
            }
        ]
    }

    def fake_chat(**kwargs):
        assert kwargs["format"] == "json"
        return {"message": {"content": json.dumps(payload)}}

    quiz = generate_quiz(
        explanation="Use pi/180.",
        citations=[{"problem_id": "Problem 4-A.11"}],
        learning_goal=None,
        quiz_size=1,
        chat=fake_chat,
    )

    assert quiz[0].source_problem_ids == ["Problem 4-A.11"]


def test_generate_quiz_rejects_invalid_model_response():
    with pytest.raises(LearningServiceError):
        generate_quiz(
            explanation="Use pi/180.",
            citations=[],
            learning_goal=None,
            quiz_size=1,
            chat=lambda **_: {"message": {"content": "not json"}},
        )
