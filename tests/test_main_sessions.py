from fastapi.testclient import TestClient

from main import app, quiz_sessions


def test_local_quiz_session_endpoints_return_progress_route():
    quiz_sessions._sessions.clear()
    client = TestClient(app)
    created = client.post("/local-quiz-sessions", json={"answer_key": [1, 0]}).json()
    result = client.post(
        f"/local-quiz-sessions/{created['session_id']}/submit",
        json={"selected_choice_indexes": [1, 0]},
    )

    assert result.status_code == 200
    assert result.json()["route"] == "advance"
