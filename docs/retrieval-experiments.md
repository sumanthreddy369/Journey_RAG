# Retrieval experiments

## BGE collection build

```mermaid
flowchart LR
    A[chunks.json] --> B[bge_ingest.py]
    B --> C[SentenceTransformer BGE model]
    C --> D[journey_textbook_bge_v1]
    D --> E[Qdrant BGE vectors]
```

**Versioning**: `bge_ingest.py` refuses to overwrite
`journey_textbook_bge_v1`. This prevents the BGE experiment from changing the
baseline `journey_textbook` collection.

**Model download**: `SentenceTransformer` resolves `BAAI/bge-small-en-v1.5` at
runtime. The model is not part of the repository.

## Hybrid ranking utilities

```mermaid
flowchart LR
    A[Question] --> B[BM25Index.search]
    A --> C[Qdrant dense result list]
    B --> D[reciprocal_rank_fusion]
    C --> D
    D --> E[Ranked chunk identifiers]
```

**Status**: **Partial**. `BM25Index` and `reciprocal_rank_fusion` are tested
utilities. `query.py` does not currently call them, so the default `/ask` path
remains Qdrant-only.

## ONNX reranking

```mermaid
flowchart TD
    A[query.search] --> B{JOURNEY_ONNX_RERANKER_DIR set?}
    B -->|no| C[Return Qdrant ordering]
    B -->|yes| D[Retrieve at least 10 candidates]
    D --> E[OnnxCrossEncoderReranker.rerank]
    E --> F[Return top_k candidates]
```

**Fallback**: an unset environment variable skips reranking. A configured path
must contain `model.onnx` or `onnx/model.onnx`; otherwise construction raises a
file error. The adapter uses the CPU execution provider.

## Offline evaluation

```mermaid
flowchart LR
    A[evals/retrieval_cases.json] --> B[load_cases]
    B --> C[Rankings from one retrieval method]
    C --> D[score_rankings]
    D --> E[Recall at k, MRR, NDCG at k]
```

**Rules**: use the same labeled cases and `k` across comparisons. The included
file is only a three-case seed set. It is not sufficient to establish a quality
claim by itself.
