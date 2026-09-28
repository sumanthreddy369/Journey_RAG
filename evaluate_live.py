"""Score labeled retrieval cases against the running local Qdrant/Ollama path."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from evaluation import RetrievalCase, load_cases, score_rankings
from retrieval import stable_chunk_id

ROOT = Path(__file__).resolve().parent


def baseline_hit_id(hit: Any, chunks: list[dict[str, Any]]) -> str:
    """Map a baseline Qdrant point back to its checked-in chunk, validating metadata."""
    index = int(hit.id)
    chunk = chunks[index]
    payload = hit.payload or {}
    for field in ("source_pdf", "page_number", "problem_id"):
        if payload.get(field) != chunk.get(field):
            raise ValueError(f"Qdrant point {index} does not match chunks.json: {field}")
    return stable_chunk_id(chunk, index)


def evaluate(mode: str, top_k: int) -> dict[str, Any]:
    if mode not in {"baseline", "hybrid"}:
        raise ValueError("mode must be baseline or hybrid")
    if top_k < 1:
        raise ValueError("top_k must be positive")

    chunks = json.loads((ROOT / "chunks.json").read_text(encoding="utf-8"))
    cases: list[RetrievalCase] = load_cases(ROOT / "evals" / "retrieval_cases.json")
    valid_ids = {stable_chunk_id(chunk, index) for index, chunk in enumerate(chunks)}
    if any(not case.relevant_chunk_ids or not case.relevant_chunk_ids <= valid_ids for case in cases):
        raise ValueError("Evaluation labels must resolve to checked-in chunks")

    os.environ["JOURNEY_RETRIEVAL_MODE"] = mode
    from query import search

    rankings: list[list[str]] = []
    outcomes: list[dict[str, Any]] = []
    for case in cases:
        hits = search(case.question, top_k=top_k)
        if mode == "baseline":
            ranked_ids = [baseline_hit_id(hit, chunks) for hit in hits]
        else:
            ranked_ids = [hit.payload["chunk_id"] for hit in hits]
        rankings.append(ranked_ids)
        outcomes.append({
            "question": case.question,
            "first_relevant_rank": next(
                (rank for rank, chunk_id in enumerate(ranked_ids, 1)
                 if chunk_id in case.relevant_chunk_ids),
                None,
            ),
        })

    return {
        "mode": mode,
        "case_count": len(cases),
        "metrics": score_rankings(rankings, cases, k=top_k),
        "outcomes": outcomes,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("baseline", "hybrid"), default="baseline")
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()
    print(json.dumps(evaluate(args.mode, args.top_k), indent=2))


if __name__ == "__main__":
    main()
