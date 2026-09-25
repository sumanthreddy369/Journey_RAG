# Journey RAG — Technology Adoption Plan

This document records which technologies fit the next Journey RAG phases. A listed technology is not a claim that it is already implemented. New dependencies are added only with tests, local verification, and a demonstrated need.

## Current foundation

- FastAPI and Pydantic for typed API contracts.
- Qdrant dense-vector retrieval with Ollama `nomic-embed-text` embeddings.
- Ollama `llama3.2` for grounded explanations and learner-facing quiz generation.
- FastMCP tools for RAG search, answers, explanations, and quizzes.
- Local deterministic quiz evaluation, conditional learning routes, and in-memory quiz sessions for synthetic development data.

## Phase A — Retrieval quality and evaluation

| Technology | Role | Adoption rule |
|---|---|---|
| BM25 | Keyword retrieval alongside semantic retrieval | Add a local lexical baseline and test it against the evaluation set. |
| Hybrid retrieval | Combine vector and keyword candidates | Use only when it improves recall or ranking over dense retrieval. |
| Reciprocal Rank Fusion | Fuse BM25 and Qdrant result lists | Keep only if NDCG/MRR improve without unacceptable latency. |
| BGE reranker | Reorder a small candidate set with a cross-encoder | Add only after hybrid retrieval is benchmarked and reranking improves final ranking. |
| NDCG and MRR | Evaluate retrieval/ranking quality | Required before claiming a retrieval enhancement is beneficial. |
| HNSW tuning | Optimize the existing Qdrant index | Tune only after corpus size, latency, and recall measurements justify it. |

## Phase B — Durable learning workflow

| Technology | Role | Adoption rule |
|---|---|---|
| PostgreSQL | Durable learner-progress records and analytics | Use only after the student-data policy and retention requirements are approved. |
| SQLAlchemy 2.x | Typed persistence and asynchronous database access | Add with PostgreSQL and repository-level integration tests. |
| Alembic | Versioned schema migrations | Add when the first persistent schema is introduced. |
| psycopg 3.x | PostgreSQL driver | Use through SQLAlchemy; do not use raw SQL for normal application paths. |
| Advanced SQL | Progress trends, mastery history, and aggregate analytics | Add only to approved, privacy-reviewed reporting queries. |
| Timezone normalization | Consistent attempt timestamps | Store timestamps in UTC and convert only for display. |

## Phase C — Authorized Microsoft 365 ingestion

| Technology | Role | Adoption rule |
|---|---|---|
| Microsoft Graph | Read approved SharePoint and OneDrive material | Require course-owner approval and least-privilege permissions. |
| MSAL and OAuth 2.0 | Obtain and refresh Graph access tokens securely | Tokens remain in environment/secret storage and are never committed. |
| httpx and asyncio | Concurrent but bounded Graph requests | Add with explicit timeouts, connection limits, and cancellation behavior. |
| Tenacity | Bounded retries for transient connector failures | Retry only idempotent, recoverable requests with visible logs. |
| Docling or Unstructured | Parse supported Office documents and complex PDFs | Benchmark against `pdfplumber`; adopt one parser based on extraction quality. |
| Pandas and PyArrow | Offline ingestion/evaluation transformations | Use for batch data work, not the request-time API path. |

## Phase D — Observability and reliability

| Technology | Role | Adoption rule |
|---|---|---|
| Structured logging | Request, retrieval, connector, and error observability | Add before any external connector or persistent learner storage. |
| Langfuse | Prompt, trace, and evaluation observability | Review hosting, privacy, retention, and cost before enabling. |
| Connection pooling | Reliable database and HTTP performance | Configure only when PostgreSQL or external connectors are introduced. |

## Explicitly deferred

- **Redis:** Use only if measured cache/session contention appears after a durable backend exists.
- **Ray or distributed futures:** Not needed for the current local corpus; reconsider only for large batch ingestion.
- **Milvus:** Qdrant is the current vector-store baseline. Benchmark alternatives before replacing or duplicating it.
- **Azure Blob:** Add only when an approved cloud document-storage requirement exists.
- **ReAct agents:** Add only after the learning workflow has stable evaluation, tool permissions, and safety boundaries.

## Implementation sequence

1. Build an evaluation dataset and report baseline recall, NDCG, and MRR.
2. Add BM25 retrieval and Reciprocal Rank Fusion behind an evaluation comparison.
3. Add BGE reranking only if evaluation confirms an improvement.
4. Integrate server-side quiz sessions with FastAPI submission endpoints.
5. Approve learner-data policy, then add PostgreSQL persistence and migrations.
6. Add structured logging, retries, and bounded HTTP requests.
7. Implement the Microsoft Graph connector using approved OAuth permissions.
8. Evaluate Langfuse only after privacy and retention review.
