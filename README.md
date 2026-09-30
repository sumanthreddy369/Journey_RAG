# Journey RAG — Interactive Hybrid Learning Platform

Local Retrieval-Augmented Generation pipeline for the Journey adaptive textbook platform (CS-ERG, Michigan Tech). It retrieves MATLAB textbook chunks from Qdrant, builds a cited context, and asks a local Ollama model for an answer.

The same baseline is available through FastAPI and a local MCP server. Hybrid mode connects BGE, BM25, and RRF to the request path, with optional ONNX reranking. PostgreSQL can store anonymous quiz progress locally.

> **Current status:** the runnable baseline uses PDF extraction, textbook chunks,
> Ollama `nomic-embed-text`, Qdrant, Ollama `llama3.2`, FastAPI, and MCP. A
> separately selected hybrid path uses BGE indexing, BM25, Reciprocal Rank Fusion,
> and an optional locally exported ONNX reranker. Offline evaluation helpers are
> included. LangGraph, vLLM, SGLang, FAISS /
> Milvus adapters, fine-tuning, MLflow, DeepEval, and Microsoft 365 connectors
> are planned—not presented as completed features.

Status: **in development**. The baseline is runnable locally. Retrieval experiments are separate from the default request path.

---

## Repository structure

```text
.
├── main.py                    # FastAPI application and HTTP routes
├── static/                     # Learner-facing local web interface
│   ├── index.html              # Interactive Journey page at /app
│   ├── app.js                  # API calls and result rendering
│   └── app.css                 # Responsive interface styles
├── query.py                   # Baseline Qdrant retrieval and Ollama answer generation
├── learning.py                # Structured explanation and quiz generation
├── progress.py                # Deterministic quiz score routing
├── sessions.py                # Process-local quiz session store
├── guardrails.py              # Question, citation, and local rate-limit checks
├── mcp_server.py              # Streamable HTTP MCP resources and tools
├── extract_pdf.py             # PDF to page text and extracted_text.txt
├── chunk_pdf.py               # Problem-level chunks and metadata
├── ingest.py                  # Baseline nomic embedding ingestion into Qdrant
├── bge_ingest.py              # Separate BGE collection builder
├── retrieval.py               # BM25 and Reciprocal Rank Fusion utilities
├── hybrid_retrieval.py        # Runnable BGE + BM25 + RRF retrieval mode
├── reranker.py                # Optional ONNX cross-encoder adapter
├── evaluation.py              # Offline retrieval scoring helpers
├── retrieval_metrics.py       # Reciprocal-rank and NDCG functions
├── query_rewrite.py           # Whitespace-normalization baseline
├── chunks.json                # Generated textbook chunk corpus
├── pages.json                 # Generated per-page extracted text
├── extracted_text.txt         # Generated raw extracted text
├── evals/
│   └── retrieval_cases.json   # Eight labeled retrieval evaluation cases
├── evaluate_live.py           # Run local Qdrant/Ollama retrieval evaluation
├── tests/                     # pytest coverage for deterministic modules
├── assets/screenshots/        # Project screenshots used by this README
├── docs/
│   └── retrieval-experiments.md # Detailed experimental retrieval flows
├── requirements.txt           # Python dependency constraints
├── AGENTS.md                  # Instructions for coding agents
└── CLAUDE.md                  # Points Claude Code to AGENTS.md
```

**Generated corpus files**: `chunks.json`, `pages.json`, and `extracted_text.txt` are present in this checkout. The source PDF used by `extract_pdf.py` is not tracked here.

---

## Corpus extraction and chunking

```mermaid
flowchart LR
    subgraph source[Source]
        A[PDF file]
    end
    subgraph parsing[Parsing]
        B[extract_pdf.py]
        C[extracted_text.txt]
        D[pages.json]
    end
    subgraph chunking[Chunking]
        E[chunk_pdf.py]
        F[chunks.json]
    end
    A --> B
    B -->|page text| C
    B -->|page records| D
    C --> E
    E -->|problem chunks and metadata| F
```

The pipeline uses page markers from `extract_pdf.py`, then splits text at the `Problem chapter-set.number` pattern in `chunk_pdf.py`.

**Metadata**: each chunk includes a problem ID, chapter, topic, set, page number, and source-PDF name. `chunk_pdf.py` assigns page `0` when no preceding page marker exists.

**Status**: **Complete** for the checked-in generated corpus. A clean re-extraction is **Partial** because the hard-coded PDF file is not in this repository.

---

## Baseline ingestion

```mermaid
flowchart TD
    A[chunks.json] --> B[ingest.py]
    B --> C[ollama.embeddings]
    C --> D[nomic-embed-text]
    D --> E{journey_textbook exists?}
    E -->|no| F[Create 768-dimensional cosine collection]
    E -->|yes| G[Reuse collection]
    F --> H[Upload points in batches of 20]
    G --> H
    H --> I[Qdrant at localhost port 6333]
```

The baseline stores up to 2,000 text characters and citation metadata per Qdrant point. It keeps the current collection name `journey_textbook`.

**Failure handling**: `ingest.py` catches an embedding error per chunk, prints it, and continues. It does not delete existing Qdrant points.

**Status**: **Complete** as a script. It requires a running Qdrant service and an Ollama model named `nomic-embed-text`.

---

## HTTP answer request

```mermaid
flowchart TD
    A[POST /ask] --> B[main.ask]
    B --> C[validate_question]
    C --> D[SlidingWindowRateLimiter.check]
    D --> E[query.ask_journey]
    E --> F[query.search]
    F --> G[ollama.embeddings]
    G --> H[Qdrant query_points]
    H --> I[Build cited context]
    I --> J[ollama.chat llama3.2]
    J --> K[validate_citations]
    K --> L[answer and citations]
    C -->|guardrail violation| M[HTTP 400]
    D -->|rate limit exceeded| M
```

The API validates the learner question before it calls an external service. `query.ask_journey` instructs the model to use only retrieved textbook context.

**Validation**: blank questions, questions longer than 1,000 characters, and a small fixed list of injection phrases are rejected. The in-memory limiter allows 20 requests per client ID per 60 seconds.

**Citation rule**: every response must contain at least one citation with `problem_id` and `page`; otherwise the request returns HTTP 400.

**Status**: Implemented for local HTTP use. CORS allows the local port-8003 UI origins. `/health` reports application liveness, not model or database readiness.

---

## Learning and quiz generation

```mermaid
flowchart TD
    A[POST /learn or MCP tool] --> B[LearningRequest]
    B --> C[create_learning_response]
    C --> D[query.ask_journey]
    D --> E[Grounded explanation and citations]
    E --> F[generate_quiz]
    F --> G[ollama.chat format json]
    G --> H{Valid quiz JSON?}
    H -->|yes| I[LearningResponse]
    H -->|no| J[LearningServiceError]
    K[QuizSubmission] --> L[evaluate_submission]
    L --> M{Score percent}
    M -->|below 60| N[reteach]
    M -->|60 to 84| O[practice]
    M -->|85 or above| P[advance]
```

Quiz generation starts from the cited explanation instead of directly from an ungrounded prompt. The learner-facing quiz model excludes answer keys.

**Schema checks**: quiz JSON must contain the requested number of questions, with two to four choices per question. Invalid model JSON raises `LearningServiceError` and `/learn` maps it to HTTP 503.

**Progress**: `progress.py` scores quizzes, while `sessions.py` keeps answer keys and the first completed attempt in memory. Optional PostgreSQL history stores five anonymous fields after scoring. See [local progress setup](docs/progress-history.md). Answer keys and unfinished sessions are lost on restart.

---

## MCP tool request

```mermaid
flowchart TD
    A[MCP client] --> B[mcp_server.py]
    B --> C{Tool or resource}
    C -->|journey status| D[get_journey_status]
    C -->|search textbook| E[search_textbook]
    C -->|ask textbook| F[ask_textbook]
    C -->|explain topic| G[explain_topic]
    C -->|create quiz| H[create_quiz]
    E --> I[_load_query_functions]
    F --> I
    I --> J[query.py]
    G --> K[learning.py]
    H --> K
    J --> L[Qdrant and Ollama]
    K --> L
    L -->|service error| M[status unavailable]
```

The MCP server binds to `127.0.0.1:8001` and uses Streamable HTTP. Query imports are lazy so unavailable local services are reported in the result instead of preventing MCP startup.

**Limits**: `search_textbook` clamps `top_k` to 1 through 10. Blank questions return `invalid_request`.

**Status**: **Complete** for the listed read-only tools. It does not write to the Qdrant collection or persist learner data.

---

## Experimental retrieval path

```mermaid
flowchart LR
    subgraph corpus[Corpus]
        A[chunks.json]
    end
    subgraph experiment[Experiment modules]
        B[bge_ingest.py]
        C[BM25Index]
        D[reciprocal_rank_fusion]
        E[OnnxCrossEncoderReranker]
        F[evaluation.py]
    end
    A --> B
    B --> G[journey_textbook_bge_v1]
    A --> C
    G --> D
    C --> D
    D --> E
    D --> F
    E --> F
```

The experimental modules preserve the baseline collection. BGE vectors go to a different Qdrant collection. BM25/RRF run through `query.search` only when `JOURNEY_RETRIEVAL_MODE=hybrid` is selected.

**ONNX switch**: `query.search` uses the reranker only when `JOURNEY_ONNX_RERANKER_DIR` is set. It then retrieves at least 10 Qdrant candidates and returns the requested top-k reranked results.

**Evaluation**: `evals/retrieval_cases.json` has eight source-checked cases. `score_rankings` computes Recall@k, MRR, and NDCG@k for supplied rankings; `evaluate_live.py` obtains rankings from the running local baseline or hybrid path. See [DATASET.md](DATASET.md) for the limited local comparison and compatibility warning.

**Status**: BGE builder, BM25, and RRF are implemented. Set `JOURNEY_RETRIEVAL_MODE=hybrid` before starting FastAPI to use that path. ONNX reranking requires a compatible local export selected with `JOURNEY_ONNX_RERANKER_DIR`; no export was found during this checkout's inspection. See [docs/retrieval-experiments.md](docs/retrieval-experiments.md) and [RUNTIME_PLAN.md](RUNTIME_PLAN.md) for runtime verification limits.

Set `JOURNEY_LLM_MODEL` to select an installed Ollama answer and quiz model.
See [MODEL_SELECTION.md](MODEL_SELECTION.md) for the local model benchmark command.

---

## Build requirements

- Python 3.11. The existing setup instructions use `py -3.11`.
- Ollama, with `nomic-embed-text` and `llama3.2` pulled for the baseline.
- Qdrant reachable at `http://localhost:6333`. The project uses a Docker-hosted Qdrant instance in its setup documentation.
- Optional BGE builder: `sentence-transformers` downloads `BAAI/bge-small-en-v1.5` when first run.
- Optional ONNX reranker: an exported compatible `model.onnx` and `JOURNEY_ONNX_RERANKER_DIR`.

Windows PowerShell setup:

```powershell
py -3.11 -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
ollama pull nomic-embed-text
ollama pull llama3.2
```

---

## Building and running

1. Install dependencies in a virtual environment:

```powershell
py -3.11 -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

2. Start Qdrant at `http://localhost:6333` and Ollama. Make sure these models are available:

```powershell
ollama pull nomic-embed-text
ollama pull llama3.2
```

3. Create or refresh the baseline Qdrant collection from the checked-in chunks:

```powershell
.\venv\Scripts\python.exe ingest.py
```

4. Start the HTTP API:

```powershell
.\venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8003 --no-access-log
```

To demonstrate BGE + BM25 + RRF instead of the baseline Qdrant-only path:

```powershell
$env:JOURNEY_RETRIEVAL_MODE = "hybrid"
.\venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8003 --no-access-log
```

5. Start the MCP server in a separate terminal:

```powershell
.\venv\Scripts\python.exe mcp_server.py
```

Use the explicit loopback command below for this checkout. Swagger UI is at `http://127.0.0.1:8003/docs`, and the learner interface is at `http://127.0.0.1:8003/app`. The MCP endpoint is `http://127.0.0.1:8001/mcp` when started separately.

```powershell
.\scripts\start-progress.ps1  # Optional: starts PostgreSQL and applies migrations
.\venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8003 --no-access-log
```

The setup script creates ignored local credentials in `.env.progress` and sets database environment variables in the current shell. Omit it to leave persistence disabled. Do not run multiple API workers: quiz sessions are process-local. See [progress history](docs/progress-history.md) for storage, privacy, and testing details.

---

## Commands / binaries / scripts

| Command | Purpose |
| --- | --- |
| `.\venv\Scripts\python.exe extract_pdf.py` | Extract the hard-coded PDF name into `extracted_text.txt` and `pages.json`; requires a local PDF not tracked here. |
| `.\venv\Scripts\python.exe chunk_pdf.py` | Build `chunks.json` from `extracted_text.txt`. |
| `.\venv\Scripts\python.exe ingest.py` | Embed chunks with Ollama and upload the baseline Qdrant collection. |
| `.\venv\Scripts\python.exe bge_ingest.py` | Build the separate BGE Qdrant collection. |
| `.\venv\Scripts\python.exe evaluate_live.py --mode baseline --top-k 5` | Score the running local baseline on the labeled cases. |
| `.\venv\Scripts\python.exe evaluate_live.py --mode hybrid --top-k 5` | Score the experimental hybrid path on the same cases. |
| `$env:JOURNEY_RETRIEVAL_MODE = "hybrid"` | Select the BGE + BM25 + RRF request path for the current PowerShell session. |
| `.\venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8003 --no-access-log` | Run FastAPI locally. |
| `.\venv\Scripts\python.exe mcp_server.py` | Run the local MCP server. |
| `.\venv\Scripts\python.exe -m pytest -q` | Run the pytest suite. |

### BGE retrieval experiment

The existing `journey_textbook` collection is preserved. Build a separate BGE
collection only when you are ready to run a local experiment:

```powershell
.\venv\Scripts\python.exe bge_ingest.py
```

This creates `journey_textbook_bge_v1`; it does not overwrite the baseline.
Read [ONNX_RERANKING.md](ONNX_RERANKING.md) before enabling a cross-encoder.

---

## API / usage

Health check:

```powershell
Invoke-RestMethod http://127.0.0.1:8003/health
```

Ask a grounded textbook question:

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8003/ask `
  -ContentType 'application/json' `
  -Body '{"question":"How do I convert degrees to radians in MATLAB?"}'
```

Request an explanation and quiz:

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8003/learn `
  -ContentType 'application/json' `
  -Body '{"question":"What is a scalar?","learning_goal":"Identify scalar values","quiz_size":3}'
```

`/ask` returns `answer` and `citations`. `/learn` returns an unscored explanation and quiz. `POST /learning-sessions` creates a model-generated quiz with its answer key held only in server memory; `POST /learning-sessions/{session_id}/submit` returns the deterministic `reteach`, `practice`, or `advance` route. The older `/local-quiz-sessions` endpoints remain a synthetic development demonstration.

### Interactive learner interface

Open `http://127.0.0.1:8003/app`. Ask calls `/ask`; Start guided quiz creates a generated learning session with a hidden server-side answer key. The first valid submission completes the quiz. With PostgreSQL enabled, the history panel shows saved anonymous attempts, supports refresh and pagination, and reports unavailable storage. The separate quiz-routing demo is synthetic and does not write history. No student accounts are implemented.

---

## Feature status

| Feature | Status |
| --- | --- |
| PDF extraction and problem-level chunking | Complete for checked-in outputs; source PDF is absent. |
| Baseline Qdrant retrieval with Ollama embeddings | Complete. |
| Grounded Ollama answer generation with citations | Complete. |
| FastAPI `/ask`, `/learn`, `/health` | Complete. |
| Interactive learner interface at `/app` | Complete locally. |
| Read-only Streamable HTTP MCP server | Complete. |
| Input/citation guards and in-memory limiter | Complete. |
| Model-generated quiz with server-side answer key and progress routing | Complete locally; sessions are process-local and not persistent. |
| Anonymous PostgreSQL progress history | Implemented with SQLAlchemy, psycopg, Alembic, and an interactive history panel; opt-in and local only. See runtime verification in RUNTIME_PLAN.md. |
| BGE collection builder | Complete locally; builds a separate collection when Qdrant is running. |
| BM25 and Reciprocal Rank Fusion | Complete locally; selected with `JOURNEY_RETRIEVAL_MODE=hybrid`. |
| ONNX reranker | Partial; adapter exists, local ONNX model is required. |
| Query rewriting | Stubbed; current function only normalizes whitespace. |
| FAISS, Milvus, pgvector adapters | Target (not built yet). |
| LangGraph agents, vLLM, SGLang, fine-tuning, MLflow, DeepEval | Target (not built yet). |
| Microsoft 365 connector | Target (not built yet). |

---

## Testing

Run:

```powershell
.\venv\Scripts\python.exe -m pytest -q
```

Tests live in `tests/`. They cover guardrails, learning JSON parsing, MCP request handling, deterministic progress routing, local session behavior, reranker ordering, retrieval metrics, BM25, RRF, and evaluation helpers. The suite uses fakes for external services; it does not require a live Qdrant instance or Ollama server.

## Project screenshots

### End-to-end architecture

![Journey RAG end-to-end flow](assets/screenshots/01-system-flow.png)

### Qdrant running in Docker

![Journey Qdrant Docker container](assets/screenshots/02-qdrant-docker.png)

### FastAPI RAG question and cited answer

![FastAPI RAG response](assets/screenshots/03-fastapi-rag-answer.png)

### Local Ollama models

![Ollama models used by Journey RAG](assets/screenshots/04-ollama-models.png)

### MCP server implementation

![Journey MCP server code](assets/screenshots/05-mcp-server-code.png)
