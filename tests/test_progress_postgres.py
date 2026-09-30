"""Opt-in real PostgreSQL test; use a dedicated database ending in _test."""
from datetime import datetime, timezone
import os
from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import delete, inspect
from sqlalchemy.engine import make_url
from learning import LearningResponse, LearningSessionDraft, QuizItem
from sessions import LocalQuizSessionStore

import main
import progress_history as history
from progress import QuizSubmission, evaluate_submission


def test_postgres_migration_persistence_idempotency_and_api(monkeypatch):
    url = os.getenv("JOURNEY_TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set JOURNEY_TEST_DATABASE_URL for the real PostgreSQL test")
    assert make_url(url).database.endswith("_test"), "Use a dedicated test database"
    monkeypatch.setenv("JOURNEY_DATABASE_URL", url)
    command.upgrade(Config(str(Path(__file__).parents[1] / "alembic.ini")), "head")
    timestamp = datetime.now(timezone.utc)
    result = evaluate_submission(QuizSubmission(selected_choice_indexes=[0]), [0])
    try:
        assert history.save_progress("MATLAB fundamentals", result, timestamp)
        assert history.save_progress("MATLAB fundamentals", result, timestamp)
        history._engine(url).dispose()
        history._engine.cache_clear()
        columns = inspect(history._engine(url)).get_columns("progress_history")
        assert {column["name"] for column in columns} == {"topic_label", "score", "route", "recommendation", "timestamp"}
        response = TestClient(main.app).get("/progress-history?limit=100")
        assert response.status_code == 200
        matches = [entry for entry in response.json() if datetime.fromisoformat(entry["timestamp"].replace("Z", "+00:00")) == timestamp]
        assert len(matches) == 1
        assert matches[0]["score"] == 100
    finally:
        with history._engine(url).begin() as connection:
            connection.execute(delete(history.history).where(history.history.c.timestamp == timestamp))


def test_generated_session_submission_persists_to_postgres(monkeypatch):
    url = os.getenv("JOURNEY_TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set JOURNEY_TEST_DATABASE_URL for the real PostgreSQL test")
    assert make_url(url).database.endswith("_test")
    monkeypatch.setenv("JOURNEY_DATABASE_URL", url)
    command.upgrade(Config(str(Path(__file__).parents[1] / "alembic.ini")), "head")
    store = LocalQuizSessionStore()
    monkeypatch.setattr(main, "quiz_sessions", store)
    draft = LearningSessionDraft(answer_key=[0], response=LearningResponse(
        explanation="A scalar is one value.",
        citations=[{"problem_id": "3-A.1", "page": 7}],
        quiz=[QuizItem(question="Which is a scalar?", choices=["5", "[1 2]"], source_problem_ids=["3-A.1"])],
        next_action="Answer the quiz.",
    ))
    monkeypatch.setattr(main, "create_learning_session", lambda _: draft)
    client = TestClient(main.app)
    created = client.post("/learning-sessions", json={"question": "Synthetic private question", "quiz_size": 1})
    assert created.status_code == 200
    session_id = created.json()["session_id"]
    try:
        for _ in range(2):
            scored = client.post(f"/learning-sessions/{session_id}/submit", json={"selected_choice_indexes": [0]})
            assert scored.status_code == 200
            assert scored.json()["progress_saved"] is True
        timestamp = store._sessions[session_id].timestamp
        entries = history.read_progress(100, 0)
        matching = [entry for entry in entries if entry.timestamp == timestamp]
        assert len(matching) == 1
        assert matching[0].topic_label == "MATLAB fundamentals"
        assert "Synthetic private question" not in matching[0].model_dump_json()
    finally:
        timestamp = store._sessions[session_id].timestamp
        if timestamp is not None:
            with history._engine(url).begin() as connection:
                connection.execute(delete(history.history).where(history.history.c.timestamp == timestamp))
