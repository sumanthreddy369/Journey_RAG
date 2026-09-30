# Local runtime plan

## Latest runtime audit — September 30, 2026

The baseline learning workflow is live and verified locally:

| Component | Current evidence |
| --- | --- |
| Ollama | Port 11434; `llama3.2:latest`, `nomic-embed-text:latest`, and `qwen3:14b` installed. |
| Qdrant | Docker `journey-qdrant` on `127.0.0.1:6333`; `journey_textbook` contains 284 points. |
| FastAPI/UI | Running at `127.0.0.1:8003`; real answer, quiz, submission, and history APIs exercised. |
| PostgreSQL | Docker `journey-progress-postgres-1` healthy on `127.0.0.1:5435`; history survived an API restart. |
| End-to-end result | Three-question quiz created, answer key absent from response, 33% routed to `reteach`, and history grew from five to six rows. |
| Generic library | Two-source live test extracted, chunked, embedded, stored, and answered with a source/page citation in `journey_textbooks_test_v1`. |
| Tests | **57 passed**, including real PostgreSQL migration and API tests. |

Ollama quiz output is constrained with a JSON schema and retried once if semantic
validation still fails. The expected source PDF and ONNX export remain absent.
The BGE collection and MCP runtime were not started in this verification. See
[workflow audit](WORKFLOW.md).

## Earlier successful verification — September 29, 2026

The repository started clean at `a6a1793` (`feat: add secure generated learning
sessions`). Older runtime claims described another laptop; they are not evidence
that its services or model files exist here.

| Component | Current verification |
| --- | --- |
| FastAPI | Running at `http://127.0.0.1:8003`; `/health`, `/docs`, and `/progress-history` returned HTTP 200. |
| Interactive UI | `/app` opened in the browser; persisted history and Refresh verified. |
| PostgreSQL | Docker PostgreSQL 16, `journey-progress-postgres-1`, published only on `127.0.0.1:5435`. |
| Progress schema | Alembic revision `0001` applied. Exactly five history columns: topic label, score, route, recommendation, UTC timestamp. |
| Tests | 47 passed, including real PostgreSQL tests against a separate `journey_test` database. Model generation is stubbed in submission integration tests. |
| Python | Project targets Python 3.11. This checkout's fresh ignored venv uses the available bundled Python 3.12; 3.11 was not available for this run. |
| Baseline retrieval | Implemented with `journey_textbook`; no Qdrant or Ollama listener found during inspection. Not exercised live here. |
| Hybrid retrieval | Implemented and selected by `JOURNEY_RETRIEVAL_MODE=hybrid`; live BGE retrieval not verified here. |
| ONNX reranker | Adapter exists; `models/bge-reranker-onnx/model.onnx` was absent. |
| MCP | Code binds `127.0.0.1:8001`; covered by tests, not started during this task. |

## Run the local progress feature

```powershell
.\scripts\start-progress.ps1
.\venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8003 --no-access-log
```

The setup script requires Docker Desktop and installed Python requirements. It
creates ignored credentials in `.env.progress`, starts an isolated Compose
project, imports the database URL into the current shell, and runs migrations.
The database volume is outside Git. No other project's containers are changed.

Open:

- Learner UI: `http://127.0.0.1:8003/app`
- API docs: `http://127.0.0.1:8003/docs`
- History: `http://127.0.0.1:8003/progress-history`

See [progress history](docs/progress-history.md) for privacy, retention,
pagination, failure behavior, and test setup. History is shared anonymously
within this local installation. Sessions and answer keys remain in memory.

## Enable retrieval only after its dependencies are ready

Qdrant must be available on port 6333 and have the appropriate ingested collection.
Ollama must have `llama3.2` and, for baseline retrieval, `nomic-embed-text`.

```powershell
# Optional hybrid mode; requires the separately ingested BGE collection.
$env:JOURNEY_RETRIEVAL_MODE = "hybrid"
# Optional reranking; set only when a compatible exported model exists.
$env:JOURNEY_ONNX_RERANKER_DIR = "$PWD\models\bge-reranker-onnx"
```

A running API or successful `/health` response does not establish retrieval or
model readiness. The existing baseline collection is preserved. No ingestion
or model download was performed as part of the progress feature.

## Planned, not implemented

Identity-linked learner profiles, automatic retention/deletion UI, analytics,
LangGraph, fine-tuning, vLLM/SGLang, alternate vector adapters, MLflow, DeepEval,
and Microsoft 365 ingestion remain outside the implemented workflow. Anonymous
PostgreSQL progress storage does not imply these features exist.
