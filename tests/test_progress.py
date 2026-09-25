import pytest

from progress import QuizSubmission, evaluate_submission


def test_low_score_routes_to_reteach():
    evaluation = evaluate_submission(QuizSubmission(selected_choice_indexes=[0, 0, 0]), [1, 1, 1])
    assert evaluation.score_percent == 0
    assert evaluation.route == "reteach"


def test_partial_score_routes_to_practice():
    evaluation = evaluate_submission(QuizSubmission(selected_choice_indexes=[1, 0, 1]), [1, 1, 1])
    assert evaluation.score_percent == 67
    assert evaluation.route == "practice"


def test_high_score_routes_to_advance():
    evaluation = evaluate_submission(QuizSubmission(selected_choice_indexes=[1, 1, 1]), [1, 1, 1])
    assert evaluation.route == "advance"


def test_answer_count_must_match_quiz():
    with pytest.raises(ValueError, match="count"):
        evaluate_submission(QuizSubmission(selected_choice_indexes=[1]), [1, 0])
