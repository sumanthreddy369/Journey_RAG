import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from evaluate_live import baseline_hit_id
from evaluation import RetrievalCase, load_cases, recall_at_k, score_rankings
from query_rewrite import rewrite_query
from retrieval import (
    BM25Index,
    LexicalDocument,
    reciprocal_rank_fusion,
    stable_chunk_id,
)

ROOT = Path(__file__).resolve().parents[1]


def test_bm25_prioritizes_keyword_match():
    index = BM25Index([
        LexicalDocument("scalar", "A scalar is one number in MATLAB.", {}),
        LexicalDocument("vector", "A vector has multiple values and direction.", {}),
    ])
    results = index.search("What is a MATLAB scalar?")
    assert results[0][0].chunk_id == "scalar"


def test_rrf_rewards_documents_present_in_multiple_rankings():
    assert reciprocal_rank_fusion([["a", "b"], ["b", "c"]], top_k=3) == ["b", "a", "c"]


def test_evaluation_reports_retrieval_metrics():
    cases = [RetrievalCase("scalar", {"scalar"}), RetrievalCase("vector", {"vector"})]
    scores = score_rankings([["scalar"], ["other", "vector"]], cases, k=2)
    assert scores == {"recall_at_2": 1.0, "mrr": 0.75, "ndcg_at_2": 0.8154648767857288}
    assert recall_at_k(["other", "vector"], {"vector"}, 1) == 0.0


def test_query_rewrite_keeps_the_original_meaning_in_baseline():
    assert rewrite_query("  Explain   vectors in MATLAB  ") == "Explain vectors in MATLAB"


def test_retrieval_labels_resolve_to_checked_in_chunks():
    chunks = json.loads((ROOT / "chunks.json").read_text(encoding="utf-8"))
    valid_ids = {stable_chunk_id(chunk, index) for index, chunk in enumerate(chunks)}
    cases = load_cases(ROOT / "evals" / "retrieval_cases.json")

    assert len(cases) == 8
    assert len({case.question for case in cases}) == len(cases)
    assert all(case.relevant_chunk_ids and case.relevant_chunk_ids <= valid_ids for case in cases)


def test_live_evaluation_rejects_stale_baseline_payload():
    chunks = [{"source_pdf": "book.pdf", "page_number": 2, "problem_id": "P1"}]
    matching = SimpleNamespace(id=0, payload=chunks[0])
    stale = SimpleNamespace(id=0, payload={**chunks[0], "page_number": 3})

    assert baseline_hit_id(matching, chunks) == "book.pdf:2:P1:0"
    with pytest.raises(ValueError, match="does not match"):
        baseline_hit_id(stale, chunks)
