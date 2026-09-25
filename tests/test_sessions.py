import pytest

from progress import QuizSubmission
from sessions import LocalQuizSessionStore


def test_session_holds_answer_key_on_server_and_evaluates_submission():
    store = LocalQuizSessionStore()
    session_id = store.create([1, 0, 1])

    evaluation = store.evaluate(session_id, QuizSubmission(selected_choice_indexes=[1, 0, 1]))

    assert evaluation.score_percent == 100
    assert evaluation.route == "advance"


def test_unknown_session_is_rejected():
    with pytest.raises(KeyError, match="not found"):
        LocalQuizSessionStore().evaluate("missing", QuizSubmission(selected_choice_indexes=[0]))
