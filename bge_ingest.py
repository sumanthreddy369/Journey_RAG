"""Build a separate BGE-backed Qdrant collection without touching the baseline."""

from __future__ import annotations

import json
from pathlib import Path

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from retrieval import stable_chunk_id

BGE_MODEL = "BAAI/bge-small-en-v1.5"
BGE_COLLECTION = "journey_textbook_bge_v1"
QDRANT_URL = "http://localhost:6333"


def build_bge_collection(chunks_path: str = "chunks.json") -> None:
    """Encode textbook chunks with BGE and upload them to a new collection."""
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise RuntimeError("Install sentence-transformers before building the BGE collection.") from exc

    chunks = json.loads(Path(chunks_path).read_text(encoding="utf-8"))
    model = SentenceTransformer(BGE_MODEL)
    vectors = model.encode(
        [f"passage: {chunk['text']}" for chunk in chunks],
        normalize_embeddings=True,
        show_progress_bar=True,
    )
    client = QdrantClient(url=QDRANT_URL)
    if client.collection_exists(BGE_COLLECTION):
        raise RuntimeError(f"{BGE_COLLECTION} already exists; keep it for reproducibility or use a new version name.")
    client.create_collection(
        collection_name=BGE_COLLECTION,
        vectors_config=VectorParams(size=len(vectors[0]), distance=Distance.COSINE),
    )
    points = [
        PointStruct(
            id=position,
            vector=vector.tolist(),
            payload={**chunk, "chunk_id": stable_chunk_id(chunk, position)},
        )
        for position, (chunk, vector) in enumerate(zip(chunks, vectors, strict=True))
    ]
    client.upload_points(collection_name=BGE_COLLECTION, points=points, batch_size=64)
    print(f"Created {BGE_COLLECTION} with {len(points)} BGE vectors.")


if __name__ == "__main__":
    build_bge_collection()
