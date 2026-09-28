# Retrieval Engineering Milestone

This milestone preserves the current `journey_textbook` collection backed by
Ollama `nomic-embed-text`. It introduces an experimental BGE collection rather
than mixing incompatible embedding vectors in the active collection.

```text
chunks.json
  -> bge_ingest.py -> journey_textbook_bge_v1 (Qdrant dense retrieval)
  -> BM25Index      -> local keyword retrieval
  -> reciprocal_rank_fusion
  -> optional ONNX cross-encoder reranker
  -> Ollama grounded answer with citations
```

## Build the BGE collection

```powershell
pip install -r requirements.txt
python bge_ingest.py
```

The BGE model downloads when the builder first runs. The collection builder
refuses to overwrite an existing collection. Use a new version name for each
material experiment so metrics remain reproducible.

## Evaluate before changing the production path

`evals/retrieval_cases.json` is a small, versioned seed set. Expand it with
human-verified questions and chunk IDs before claiming retrieval improvements.
Compare the same cases across:

1. Current Qdrant dense retrieval.
2. BGE dense retrieval.
3. BGE plus BM25 with Reciprocal Rank Fusion.
4. Hybrid retrieval plus ONNX reranking.

Record Recall@k, MRR, NDCG@k, latency, and citation correctness. FAISS,
Milvus/pgvector, LangGraph, MLflow, fine-tuning, vLLM, and SGLang remain future
milestones until they have a working adapter or runtime integration.
