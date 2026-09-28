from evaluation import RetrievalCase, recall_at_k, score_rankings
from query_rewrite import rewrite_query
from retrieval import BM25Index, LexicalDocument, reciprocal_rank_fusion


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
