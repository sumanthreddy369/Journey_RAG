from fastapi.testclient import TestClient

import main
from learning import LearningResponse, LearningSessionDraft, QuizItem, ScoredQuizItem, create_learning_session


def test_create_learning_session_keeps_answer_key_out_of_public_response():
    draft = create_learning_session(
        main.LearningRequest(question="Explain scalars", quiz_size=1),
        answerer=lambda _: ("A scalar has one value.", [{"problem_id": "Problem 3-A.1", "page": 7}]),
        quiz_generator=lambda **_: [
            ScoredQuizItem(
                question="Which is a scalar?",
                choices=["5", "[1 2]"],
                source_problem_ids=["Problem 3-A.1"],
                correct_choice_index=0,
            )
        ],
    )

    assert draft.answer_key == [0]
    assert "correct_choice_index" not in draft.response.model_dump()["quiz"][0]


def test_learning_session_routes_return_public_quiz_and_score(monkeypatch):
    main.quiz_sessions._sessions.clear()
    response = LearningResponse(
        explanation="A scalar has one value.",
        citations=[{"problem_id": "Problem 3-A.1", "page": 7}],
        quiz=[QuizItem(question="Which is a scalar?", choices=["5", "[1 2]"], source_problem_ids=["Problem 3-A.1"])],
        next_action="Answer the quiz.",
    )
    monkeypatch.setattr(main, "create_learning_session", lambda _: LearningSessionDraft(response=response, answer_key=[0]))
    client = TestClient(main.app)

    created = client.post("/learning-sessions", json={"question": "Explain scalars", "quiz_size": 1})
    assert created.status_code == 200
    body = created.json()
    assert "correct_choice_index" not in body["quiz"][0]

    scored = client.post(
        f"/learning-sessions/{body['session_id']}/submit",
        json={"selected_choice_indexes": [0]},
    )
    assert scored.status_code == 200
    assert scored.json()["route"] == "advance"
