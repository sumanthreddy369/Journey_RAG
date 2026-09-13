"""Read-only MCP interface for the existing Journey textbook RAG system."""

from typing import Any, Callable

from mcp.server.fastmcp import FastMCP

MAX_RESULTS = 10
mcp = FastMCP("Journey Textbook RAG", stateless_http=True, json_response=True)


def _load_query_functions() -> tuple[Callable[..., Any], Callable[..., Any]]:
    """Import lazily so MCP can report service availability instead of crashing."""
    from query import ask_journey, search

    return search, ask_journey


def _valid_question(question: str) -> str | None:
    normalized = question.strip()
    return normalized or None


def _citation(payload: dict[str, Any]) -> dict[str, Any]:
    """Return only textbook metadata needed to identify a retrieved passage."""
    return {
        "problem_id": payload.get("problem_id"),
        "chapter": payload.get("chapter"),
        "chapter_topic": payload.get("chapter_topic"),
        "page": payload.get("page_number"),
        "set_desc": payload.get("set_desc"),
        "source_pdf": payload.get("source_pdf"),
    }


def journey_status() -> dict[str, str]:
    """Describe the local dependencies required by the existing RAG pipeline."""
    return {
        "service": "Journey Textbook RAG",
        "transport": "Streamable HTTP",
        "endpoint": "http://127.0.0.1:8001/mcp",
        "requirements": "Qdrant at http://localhost:6333 and Ollama models nomic-embed-text and llama3.2.",
    }


@mcp.resource("journey://status")
def get_journey_status() -> dict[str, str]:
    """Read the Journey RAG service requirements and MCP endpoint details."""
    return journey_status()


@mcp.tool()
def search_textbook(question: str, top_k: int = 3) -> dict[str, Any]:
    """Retrieve relevant MATLAB textbook passages from Journey's existing Qdrant collection."""
    normalized = _valid_question(question)
    if normalized is None:
        return {"status": "invalid_request", "message": "Provide a non-empty question.", "results": []}

    limit = max(1, min(top_k, MAX_RESULTS))
    try:
        search, _ = _load_query_functions()
        hits = search(normalized, top_k=limit)
    except Exception as exc:
        return {
            "status": "unavailable",
            "message": "Journey retrieval is unavailable. Start Qdrant and Ollama, then verify the textbook collection.",
            "detail": str(exc),
            "results": [],
        }

    results = []
    for hit in hits:
        payload = hit.payload or {}
        results.append({"text": payload.get("text", ""), "citation": _citation(payload), "score": getattr(hit, "score", None)})
    return {"status": "ok", "query": normalized, "results": results}


@mcp.tool()
def ask_textbook(question: str) -> dict[str, Any]:
    """Answer a MATLAB textbook question through Journey's grounded RAG pipeline."""
    normalized = _valid_question(question)
    if normalized is None:
        return {"status": "invalid_request", "message": "Provide a non-empty question."}

    try:
        _, ask_journey = _load_query_functions()
        answer, citations = ask_journey(normalized)
    except Exception as exc:
        return {"status": "unavailable", "message": "Journey answering is unavailable. Start Qdrant and Ollama, then verify the textbook collection.", "detail": str(exc)}
    return {"status": "ok", "answer": answer, "citations": citations}


def main() -> None:
    """Serve MCP locally without exposing the textbook RAG service to the network."""
    mcp.run(transport="streamable-http", host="127.0.0.1", port=8001)


if __name__ == "__main__":
    main()
