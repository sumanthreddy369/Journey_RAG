from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient
import pytest

import main
import progress_history as history
from progress import QuizSubmission
from sessions import LocalQuizSessionStore


@pytest.fixture(autouse=True)
def disable_database(monkeypatch):
    monkeypatch.delenv("JOURNEY_DATABASE_URL", raising=False)


@pytest.mark.parametrize("url", [
    "postgresql+psycopg://user:secret@remote.example/db",
    "sqlite:///history.db",
    "postgresql+psycopg://localhost/db?host=remote.example",
    "not a database url",
])
def test_nonlocal_configuration_is_rejected_without_leaking_credentials(monkeypatch, url):
    monkeypatch.setenv("JOURNEY_DATABASE_URL", url)
    with pytest.raises(history.HistoryUnavailable) as error:
        history.database_url()
    assert "secret" not in str(error.value)


def test_topic_is_taken_only_from_corpus_labels():
    topic = next(iter(history._topics()))
    assert history.textbook_topic([{"chapter_topic": topic}]) == topic
    assert history.textbook_topic([{"chapter_topic": "My name is Private Person"}]) == "MATLAB fundamentals"
    assert history.textbook_topic([{"chapter_topic": "Private filename", "set_desc": "Textbook passage"}]) == "General textbook study"


def test_history_disabled_and_pagination_validation():
    client = TestClient(main.app)
    assert client.get("/progress-history").status_code == 503
    for query in ("limit=0", "limit=101", "offset=-1"):
        assert client.get(f"/progress-history?{query}").status_code == 422


def test_history_response_has_only_allowed_fields(monkeypatch):
    entry = history.HistoryEntry(topic_label="MATLAB", score=100, route="advance",
                                 recommendation="Practice", timestamp=datetime.now(timezone.utc))
    monkeypatch.setattr(main, "read_progress", lambda limit, offset: [entry])
    response = TestClient(main.app).get("/progress-history")
    assert response.status_code == 200
    assert set(response.json()[0]) == {"topic_label", "score", "route", "recommendation", "timestamp"}
    assert response.json()[0]["timestamp"].endswith("Z")


def test_scoring_survives_outage_and_retries_only_first_attempt(monkeypatch):
    store = LocalQuizSessionStore()
    monkeypatch.setattr(main, "quiz_sessions", store)
    session_id = store.create([0], topic="MATLAB fundamentals")
    attempts = []

    def unavailable(topic, score, timestamp):
        attempts.append(timestamp)
        raise history.HistoryUnavailable("Progress could not be saved.")

    monkeypatch.setattr(main, "save_progress", unavailable)
    client = TestClient(main.app)
    path = f"/learning-sessions/{session_id}/submit"
    response = client.post(path, json={"selected_choice_indexes": [0]})
    assert response.status_code == 200
    assert response.json()["score_percent"] == 100
    assert response.json()["progress_saved"] is False

    def available(topic, score, timestamp):
        attempts.append(timestamp)
        assert score.score_percent == 100
        return True

    monkeypatch.setattr(main, "save_progress", available)
    for _ in range(2):
        response = client.post(path, json={"selected_choice_indexes": [1]})
        assert response.json()["progress_saved"] is True
        assert response.json()["score_percent"] == 100
    assert len(attempts) == 2
    assert attempts[0] == attempts[1]


def test_concurrent_submissions_save_once():
    store = LocalQuizSessionStore()
    session_id = store.create([0], topic="MATLAB fundamentals")
    saved = []

    def recorder(*args):
        saved.append(args)
        return True

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: store.complete(session_id, QuizSubmission(selected_choice_indexes=[0]), recorder), range(8)))
    assert len(saved) == 1
    assert all(result.score_percent == 100 and recorded for result, recorded in results)


def test_invalid_or_synthetic_sessions_never_persist():
    store = LocalQuizSessionStore()
    session_id = store.create([0, 1], topic="MATLAB fundamentals")

    def recorder(*args):
        pytest.fail("Invalid submission must not be saved")

    with pytest.raises(ValueError):
        store.complete(session_id, QuizSubmission(selected_choice_indexes=[0]), recorder)
    with pytest.raises(KeyError):
        store.complete(store.create([0]), QuizSubmission(selected_choice_indexes=[0]), recorder)
