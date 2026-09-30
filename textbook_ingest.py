"""Generic multi-textbook extraction, chunking, embedding, and Qdrant ingestion."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from hashlib import sha256
import os
from pathlib import Path
import re
from typing import Callable, Iterable
from uuid import NAMESPACE_URL, uuid5

import ollama
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

LIBRARY_COLLECTION = "journey_textbooks_v1"
SUPPORTED_SUFFIXES = {".pdf", ".txt", ".md", ".markdown"}
EMBED_MODEL = "nomic-embed-text"
QDRANT_URL = "http://127.0.0.1:6333"
MAX_CHUNK_CHARS = 1_800
CHUNK_OVERLAP_CHARS = 200
UPLOAD_BATCH_SIZE = 32


@dataclass(frozen=True)
class TextbookPage:
    page_number: int
    text: str


@dataclass(frozen=True)
class IngestedBook:
    source_name: str
    pages: int
    chunks: int


def discover_textbooks(inputs: Iterable[str | Path]) -> list[Path]:
    """Resolve supported files from files or directories, recursively and deterministically."""
    discovered: dict[Path, Path] = {}
    for raw_input in inputs:
        path = Path(raw_input).expanduser()
        if not path.exists():
            raise FileNotFoundError(f"Textbook input was not found: {path}")
        candidates = path.rglob("*") if path.is_dir() else [path]
        for candidate in candidates:
            if candidate.is_file() and candidate.suffix.lower() in SUPPORTED_SUFFIXES:
                resolved = candidate.resolve()
                discovered[resolved] = resolved
    if not discovered:
        supported = ", ".join(sorted(SUPPORTED_SUFFIXES))
        raise ValueError(f"No supported textbooks were found. Supported types: {supported}.")
    return sorted(discovered.values(), key=lambda item: str(item).casefold())


def extract_pages(path: Path) -> list[TextbookPage]:
    """Extract searchable text while retaining the source page number."""
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        try:
            import pdfplumber
        except ImportError as exc:
            raise RuntimeError("Install pdfplumber to ingest PDF textbooks.") from exc
        with pdfplumber.open(path) as pdf:
            pages = [
                TextbookPage(page_number=index, text=text)
                for index, page in enumerate(pdf.pages, start=1)
                if (text := page.extract_text()) and text.strip()
            ]
    else:
        pages = [TextbookPage(page_number=1, text=path.read_text(encoding="utf-8"))]
    if not pages:
        raise ValueError(
            f"No searchable text was found in {path.name}. Scanned PDFs need OCR before ingestion."
        )
    return pages


def chunk_text(text: str, *, max_chars: int = MAX_CHUNK_CHARS,
               overlap_chars: int = CHUNK_OVERLAP_CHARS) -> list[str]:
    """Create bounded overlapping chunks without depending on a book-specific layout."""
    if max_chars < 200:
        raise ValueError("max_chars must be at least 200.")
    if overlap_chars < 0 or overlap_chars >= max_chars:
        raise ValueError("overlap_chars must be nonnegative and smaller than max_chars.")
    normalized = re.sub(r"\s+", " ", text).strip()
    if not normalized:
        return []

    chunks: list[str] = []
    start = 0
    while start < len(normalized):
        proposed_end = min(start + max_chars, len(normalized))
        end = proposed_end
        if proposed_end < len(normalized):
            boundary = normalized.rfind(" ", start + max_chars // 2, proposed_end)
            if boundary > start:
                end = boundary
        chunk = normalized[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(normalized):
            break
        next_start = max(start + 1, end - overlap_chars)
        boundary = normalized.find(" ", next_start, end)
        start = boundary + 1 if boundary != -1 else end
    return chunks


def source_key(path: Path) -> str:
    """Create a stable replacement key without storing the local absolute path."""
    return sha256(str(path.resolve()).casefold().encode("utf-8")).hexdigest()


def build_payloads(path: Path, pages: list[TextbookPage]) -> list[dict[str, object]]:
    """Build generic citation-compatible payloads for every extracted page."""
    key = source_key(path)
    title = path.stem.replace("_", " ").strip() or path.name
    payloads: list[dict[str, object]] = []
    for page in pages:
        for chunk_index, text in enumerate(chunk_text(page.text), start=1):
            passage = f"{title} - page {page.page_number} - passage {chunk_index}"
            payloads.append({
                "text": text,
                "problem_id": passage,
                "chapter": "",
                "chapter_topic": title[:120],
                "set": "",
                "set_desc": "Textbook passage",
                "page_number": page.page_number,
                "source_pdf": path.name,
                "source_name": path.name,
                "source_key": key,
                "chunk_index": chunk_index,
            })
    if not payloads:
        raise ValueError(f"No non-empty chunks were produced from {path.name}.")
    return payloads


def embed_text(text: str) -> list[float]:
    response = ollama.embeddings(model=EMBED_MODEL, prompt=text[:4_000])
    return list(response["embedding"])


def ingest_textbooks(
    inputs: Iterable[str | Path],
    *,
    collection_name: str = LIBRARY_COLLECTION,
    client: QdrantClient | None = None,
    embedder: Callable[[str], list[float]] = embed_text,
    extractor: Callable[[Path], list[TextbookPage]] = extract_pages,
) -> list[IngestedBook]:
    """Ingest each book independently and replace its previous chunks only after embedding succeeds."""
    paths = discover_textbooks(inputs)
    qdrant = client or QdrantClient(url=os.getenv("JOURNEY_QDRANT_URL", QDRANT_URL))
    results: list[IngestedBook] = []

    for path in paths:
        pages = extractor(path)
        payloads = build_payloads(path, pages)
        points: list[PointStruct] = []
        vector_size: int | None = None
        key = source_key(path)
        for index, payload in enumerate(payloads):
            vector = embedder(str(payload["text"]))
            if not vector:
                raise ValueError(f"Embedding model returned an empty vector for {path.name}.")
            vector_size = vector_size or len(vector)
            if len(vector) != vector_size:
                raise ValueError("Embedding model returned inconsistent vector dimensions.")
            point_id = str(uuid5(NAMESPACE_URL, f"journey:{key}:{payload['page_number']}:{index}"))
            points.append(PointStruct(id=point_id, vector=vector, payload=payload))

        assert vector_size is not None
        if not qdrant.collection_exists(collection_name):
            qdrant.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
            )
        else:
            configured_size = qdrant.get_collection(collection_name).config.params.vectors.size
            if configured_size != vector_size:
                raise ValueError(
                    f"Collection {collection_name} uses {configured_size}-dimension vectors; "
                    f"the current model returned {vector_size}. Use a new versioned collection."
                )

        qdrant.delete(
            collection_name=collection_name,
            points_selector=Filter(must=[
                FieldCondition(key="source_key", match=MatchValue(value=key))
            ]),
            wait=True,
        )
        for batch_start in range(0, len(points), UPLOAD_BATCH_SIZE):
            qdrant.upsert(
                collection_name=collection_name,
                points=points[batch_start:batch_start + UPLOAD_BATCH_SIZE],
                wait=True,
            )
        results.append(IngestedBook(source_name=path.name, pages=len(pages), chunks=len(points)))
    return results


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract, chunk, embed, and store one or more local textbooks."
    )
    parser.add_argument("inputs", nargs="+", help="Textbook files or directories")
    parser.add_argument("--collection", default=LIBRARY_COLLECTION)
    args = parser.parse_args()

    results = ingest_textbooks(args.inputs, collection_name=args.collection)
    print(f"Collection ready: {args.collection}")
    for result in results:
        print(f"- {result.source_name}: {result.pages} pages, {result.chunks} chunks")
    if args.collection == LIBRARY_COLLECTION:
        print("Journey will use this library automatically unless JOURNEY_COLLECTION overrides it.")
    else:
        print(f"To query this collection, set JOURNEY_COLLECTION={args.collection}.")


if __name__ == "__main__":
    main()
