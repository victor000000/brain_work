"""BRAIN_FEEDBACK_LOOP env-var gate behavior — default-on plus 0/1 overrides."""


def test_feedback_loop_enabled_by_default(monkeypatch):
    """Default-on: with BRAIN_FEEDBACK_LOOP unset, the feedback loop is active."""
    monkeypatch.delenv("BRAIN_FEEDBACK_LOOP", raising=False)
    from generator.weighted_selection import _feedback_loop_enabled

    assert _feedback_loop_enabled() is True


def test_feedback_loop_opt_out_with_zero(monkeypatch):
    """Setting =0 opts out (the rollback path)."""
    monkeypatch.setenv("BRAIN_FEEDBACK_LOOP", "0")
    from generator.weighted_selection import _feedback_loop_enabled

    assert _feedback_loop_enabled() is False


def test_feedback_loop_explicit_one_still_enabled(monkeypatch):
    """=1 stays enabled (existing call sites that explicitly set it keep working)."""
    monkeypatch.setenv("BRAIN_FEEDBACK_LOOP", "1")
    from generator.weighted_selection import _feedback_loop_enabled

    assert _feedback_loop_enabled() is True
