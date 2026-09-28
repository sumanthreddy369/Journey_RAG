"""Runnable local BGE, BM25, and RRF retrieval path for Journey RAG."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from qdrant_client import QdrantClient

from retrieval import BM25Index, LexicalDocument, reciprocal_rank_fusion, stable_chunk_id
from reranker import OnnxCrossEncoderReranker, configured_reranker

BGE_COLLECTION = "journey_textbook_bge_v1"
BGE_MODEL = "BAAI/bge-small-en-v1.5"
QDRANT_URL = "http://localhost:6333"


@dataclass
class RetrievalHit:
    """Small common result shape for dense and lexical candidates."""

    payload: dict[str, Any]
    score: float | None = None


def load_documents(chunks_path: str | Path = "chunks.json") -> list[LexicalDocument]:
    chunks = json.loads(Path(chunks_path).read_text(encoding="utf-8"))
    return [
        LexicalDocument(
            chunk_id=stable_chunk_id(chunk, position),
            text=chunk["text"],
            metadata={**chunk, "chunk_id": stable_chunk_id(chunk, position)},
        )
        for position, chunk in enumerate(chunks)
    ]


class HybridRetriever:
    """Fuse BGE dense retrieval and local BM25 without changing the baseline collection."""

    def __init__(
        self,
        *,
        documents: list[LexicalDocument] | None = None,
        encoder: Any | None = None,
        client: Any | None = None,
        reranker: OnnxCrossEncoderReranker | None = None,
    ) -> None:
        self.documents = documents or load_documents()
        self.by_id = {document.chunk_id: document for document in self.documents}
        self.bm25 = BM25Index(self.documents)
        if encoder is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as exc:
                raise RuntimeError("Install sentence-transformers to use hybrid retrieval.") from exc
            encoder = SentenceTransformer(BGE_MODEL)
        self.encoder = encoder
        self.client = client or QdrantClient(url=QDRANT_URL)
        self.reranker = reranker if reranker is not None else configured_reranker()

    def search(self, question: str, top_k: int = 3, candidate_k: int = 10) -> list[RetrievalHit]:
        if top_k < 1 or candidate_k < top_k:
            raise ValueError("candidate_k must be at least top_k and both must be positive.")
        encoded_vector = self.encoder.encode([f"query: {question}"], normalize_embeddings=True)[0]
        vector = encoded_vector.tolist() if hasattr(encoded_vector, "tolist") else list(encoded_vector)
        dense_points = self.client.query_points(
            collection_name=BGE_COLLECTION,
            query=vector,
            limit=candidate_k,
            with_payload=True,
        ).points
        dense_hits = [RetrievalHit(payload=point.payload or {}, score=float(point.score)) for point in dense_points]
        lexical_pairs = self.bm25.search(question, top_k=candidate_k)
        lexical_hits = [RetrievalHit(payload=document.metadata, score=score) for document, score in lexical_pairs]
        candidates = {
            hit.payload["chunk_id"]: hit
            for hit in [*dense_hits, *lexical_hits]
            if hit.payload.get("chunk_id")
        }
        fused_ids = reciprocal_rank_fusion(
            [[hit.payload["chunk_id"] for hit in dense_hits], [hit.payload["chunk_id"] for hit in lexical_hits]],
            top_k=candidate_k,
        )
        fused_hits = [candidates[chunk_id] for chunk_id in fused_ids if chunk_id in candidates]
        if self.reranker is not None:
            return self.reranker.rerank(question, fused_hits, top_k)
        return fused_hits[:top_k]


_retriever: HybridRetriever | None = None


def hybrid_search(question: str, top_k: int = 3) -> list[RetrievalHit]:
    """Lazily create the experimental retriever for the process."""
    global _retriever
    if _retriever is None:
        _retriever = HybridRetriever()
    return _retriever.search(question, top_k=top_k)
