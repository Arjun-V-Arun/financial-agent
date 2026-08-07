from app import feedback


def test_feedback_is_scoped_by_question_and_role(tmp_path, monkeypatch):
    monkeypatch.setattr(feedback.config, "DB_PATH", tmp_path / "facts.db")

    feedback.record("What were net sales?", "CEO", ["chunk-a"], 1)
    feedback.record("What were net sales?", "CEO", ["chunk-a"], 1)
    feedback.record("What were net sales?", "CTO", ["chunk-a"], -1)

    assert feedback.boosts("  what WERE net sales? ", "CEO") == {
        "chunk-a": 0.16
    }
    assert feedback.boosts("What were net sales?", "CTO") == {
        "chunk-a": -0.08
    }
    assert feedback.boosts("What was net income?", "CEO") == {}


def test_feedback_boost_is_bounded(tmp_path, monkeypatch):
    monkeypatch.setattr(feedback.config, "DB_PATH", tmp_path / "facts.db")

    for _ in range(10):
        feedback.record("Question", "CEO", ["chunk-a"], 1)

    assert feedback.boosts("Question", "CEO") == {
        "chunk-a": feedback.MAX_BOOST
    }