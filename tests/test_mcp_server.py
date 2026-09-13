from types import SimpleNamespace

import mcp_server


def test_search_uses_existing_retrieval_and_returns_textbook_citation(monkeypatch) -> None:
    hit = SimpleNamespace(score=0.91, payload={"text": "Use pi/180 to convert degrees to radians.", "problem_id": "Problem 3-A.1", "chapter": 3, "chapter_topic": "MATLAB Basics: Scalars", "page_number": 14, "set_desc": "Nuts and Bolts", "source_pdf": "textbook.pdf"})
    monkeypatch.setattr(mcp_server, "_load_query_functions", lambda: (lambda question, top_k: [hit], None))
    result = mcp_server.search_textbook("degrees to radians", top_k=99)
    assert result["status"] == "ok"
    assert result["results"][0]["citation"]["page"] == 14


def test_search_rejects_blank_question() -> None:
    assert mcp_server.search_textbook("   ")["status"] == "invalid_request"


def test_answer_uses_existing_rag_answer_function(monkeypatch) -> None:
    monkeypatch.setattr(mcp_server, "_load_query_functions", lambda: (None, lambda question: ("Grounded answer", [{"page": 14}])))
    assert mcp_server.ask_textbook("What is a scalar?") == {"status": "ok", "answer": "Grounded answer", "citations": [{"page": 14}]}
