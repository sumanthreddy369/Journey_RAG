from types import SimpleNamespace

from fastapi.testclient import TestClient

import main
import query


def test_active_collection_prefers_nonempty_library(monkeypatch):
    fake_client = SimpleNamespace(
        collection_exists=lambda name: True,
        get_collection=lambda name: SimpleNamespace(points_count=4),
    )
    monkeypatch.delenv("JOURNEY_COLLECTION", raising=False)
    monkeypatch.setattr(query, "client", fake_client)

    assert query.active_collection() == query.LIBRARY_COLLECTION


def test_explicit_collection_override_wins(monkeypatch):
    monkeypatch.setenv("JOURNEY_COLLECTION", "course_library_v2")
    assert query.active_collection() == "course_library_v2"


def test_library_status_reports_active_collection(monkeypatch):
    monkeypatch.setattr(query, "active_collection", lambda: "course_library_v2")
    monkeypatch.setattr(query, "client", SimpleNamespace(
        get_collection=lambda name: SimpleNamespace(points_count=42)
    ))

    assert query.library_status() == {"collection": "course_library_v2", "points": 42}


def test_library_status_endpoint(monkeypatch):
    monkeypatch.setattr(main, "library_status", lambda: {
        "collection": "journey_textbooks_v1",
        "points": 12,
    })

    response = TestClient(main.app).get("/library-status")

    assert response.status_code == 200
    assert response.json() == {"collection": "journey_textbooks_v1", "points": 12}


def test_generic_payload_produces_cited_answer(monkeypatch):
    hit = SimpleNamespace(payload={
        "text": "Feedback changes system behavior.",
        "source_name": "Control Systems.pdf",
        "page_number": 12,
        "chapter_topic": "Control Systems",
    })
    monkeypatch.setattr(query, "search", lambda question: [hit])
    monkeypatch.setattr(query.ollama, "chat", lambda **kwargs: {
        "message": {"content": "Feedback changes the response."}
    })

    answer, citations = query.ask_journey("What does feedback do?")

    assert answer == "Feedback changes the response."
    assert citations == [{
        "problem_id": "Control Systems.pdf",
        "chapter": "",
        "chapter_topic": "Control Systems",
        "page": 12,
        "set_desc": "Textbook passage",
        "source_name": "Control Systems.pdf",
    }]
