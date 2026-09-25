import pytest

from retrieval_metrics import mean_reciprocal_rank, ndcg_at_k, reciprocal_rank


def test_reciprocal_rank_uses_first_relevant_result():
    assert reciprocal_rank(["wrong", "Problem 3-A.1"], {"Problem 3-A.1"}) == 0.5


def test_mean_reciprocal_rank_averages_queries():
    score = mean_reciprocal_rank(
        [["Problem 3-A.1"], ["wrong", "Problem 4-A.11"]],
        [{"Problem 3-A.1"}, {"Problem 4-A.11"}],
    )
    assert score == 0.75


def test_ndcg_rewards_relevant_results_near_the_top():
    assert ndcg_at_k(["Problem 4-A.11", "wrong"], {"Problem 4-A.11"}, 2) == 1.0
    assert ndcg_at_k(["wrong", "Problem 4-A.11"], {"Problem 4-A.11"}, 2) < 1.0


def test_metrics_validate_inputs():
    with pytest.raises(ValueError, match="matching"):
        mean_reciprocal_rank([["one"]], [])
    with pytest.raises(ValueError, match="at least"):
        ndcg_at_k(["one"], {"one"}, 0)
