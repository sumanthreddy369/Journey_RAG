# AGENTS.md

## Project overview

Journey RAG is a Python 3.11 local textbook RAG prototype. The baseline uses
`chunks.json`, Ollama embeddings, Qdrant, and Ollama chat generation. FastAPI
exposes HTTP routes. `mcp_server.py` exposes read-only MCP tools.

## Structure map

- `main.py`: FastAPI application and HTTP routes.
- `query.py`: baseline Qdrant retrieval and grounded Ollama answer generation.
- `learning.py`, `progress.py`, `sessions.py`: local learning, quiz, and
  in-memory session primitives.
- `progress_history.py`, `migrations/`, `compose.progress.yaml`: optional
  loopback PostgreSQL history with five anonymous fields; see
  `docs/progress-history.md` for privacy constraints and real database tests.
- `guardrails.py`: deterministic input, citation, and rate-limit checks.
- `extract_pdf.py`, `chunk_pdf.py`, `ingest.py`: baseline corpus pipeline.
- `bge_ingest.py`, `retrieval.py`, `reranker.py`, `evaluation.py`: optional
  retrieval experiment components.
- `mcp_server.py`: local Streamable HTTP MCP server.
- `tests/`: pytest tests.
- `evals/`: versioned seed retrieval cases.

## Commands

```powershell
.\venv\Scripts\python.exe -m pytest -q
.\venv\Scripts\python.exe -m uvicorn main:app --reload
.\venv\Scripts\python.exe mcp_server.py
.\venv\Scripts\python.exe ingest.py
.\venv\Scripts\python.exe bge_ingest.py
```

`ingest.py` needs Qdrant on `http://localhost:6333` and Ollama with
`nomic-embed-text`. `bge_ingest.py` also downloads/loads the BGE model.

## Code conventions

- Use Python type hints for public functions and Pydantic models for HTTP or
  learner-facing payloads.
- Keep local-service dependencies lazy where availability failures should be
  returned rather than crashing a server.
- Keep exceptions narrow and preserve the current user-facing error contract.
- Keep external-service and model configuration as named module constants or
  documented environment variables.
- Add pytest coverage for new deterministic behavior.

## Do

- Preserve `journey_textbook` as the baseline collection.
- Create a new versioned collection for an incompatible embedding model.
- Keep citations tied to retrieved payload metadata.
- Keep learner data local and non-persistent unless persistence is explicitly
  designed, approved, and tested.
- Update documentation whenever implementation status changes.

## Do not

- Do not commit secrets, downloaded models, local databases, learner records,
  private PDFs, or external-service tokens.
- Do not claim experimental or planned components are active in the request
  path without a runnable integration and measured evaluation.
- Do not expose the MCP server beyond `127.0.0.1` without explicit review.
- Do not overwrite the baseline Qdrant collection when testing BGE or another
  embedding model.
