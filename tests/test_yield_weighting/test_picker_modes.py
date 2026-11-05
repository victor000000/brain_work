"""Picker mode switch: BRAIN_YIELD_WEIGHTING gates count vs yield weighting."""

import generator.diversity_picker as picker
import generator.diversity_weights as dw


def test_picker_count_mode_default(monkeypatch):
    """Without BRAIN_YIELD_WEIGHTING, picker uses count weights."""
    monkeypatch.delenv("BRAIN_YIELD_WEIGHTING", raising=False)
    fresh = dw.DiversityCache()
    fresh.region_config_weights = {("USA", "TOP3000", 1): 0.5, ("IND", "TOP500", 1): 0.5}
    fresh.region_config_yield_weights = {("USA", "TOP3000", 1): 0.001, ("IND", "TOP500", 1): 0.999}
    dw.set_state(fresh)
    try:
        configs = [("USA", "TOP3000", 1), ("IND", "TOP500", 1)]
        ind_picks = sum(1 for _ in range(200) if picker.weighted_pick_config(configs)[0] == "IND")
        # Equal count weights -> roughly 50/50; allow generous tolerance.
        assert 60 < ind_picks < 140
    finally:
        dw.set_state(dw.DiversityCache())


def test_picker_yield_mode_skews_to_high_yield(monkeypatch):
    """With BRAIN_YIELD_WEIGHTING=1, picker skews heavily toward IND."""
    monkeypatch.setenv("BRAIN_YIELD_WEIGHTING", "1")
    fresh = dw.DiversityCache()
    fresh.region_config_weights = {("USA", "TOP3000", 1): 0.5, ("IND", "TOP500", 1): 0.5}
    fresh.region_config_yield_weights = {("USA", "TOP3000", 1): 0.005, ("IND", "TOP500", 1): 0.080}
    dw.set_state(fresh)
    try:
        configs = [("USA", "TOP3000", 1), ("IND", "TOP500", 1)]
        ind_picks = sum(1 for _ in range(200) if picker.weighted_pick_config(configs)[0] == "IND")
        # IND has 16x the yield weight of USA → expect ~94% IND picks.
        assert ind_picks > 160
    finally:
        dw.set_state(dw.DiversityCache())


def test_picker_yield_mode_uses_prior_for_unknown_configs(monkeypatch):
    """Configs not in the yield dict get the prior mean — they aren't dropped."""
    monkeypatch.setenv("BRAIN_YIELD_WEIGHTING", "1")
    fresh = dw.DiversityCache()
    fresh.region_config_yield_weights = {}  # empty — every config is "unknown"
    dw.set_state(fresh)
    try:
        configs = [("USA", "TOP3000", 1), ("IND", "TOP500", 1)]
        # Should still pick (using prior) — never returns None.
        picks = [picker.weighted_pick_config(configs) for _ in range(20)]
        assert all(p in configs for p in picks)
    finally:
        dw.set_state(dw.DiversityCache())


def test_picker_yield_mode_off_when_env_falsey(monkeypatch):
    """BRAIN_YIELD_WEIGHTING=0 / empty / false stays in count mode."""
    fresh = dw.DiversityCache()
    fresh.region_config_weights = {("A", "U", 1): 1.0, ("B", "U", 1): 1.0}
    fresh.region_config_yield_weights = {("A", "U", 1): 0.999, ("B", "U", 1): 0.001}
    dw.set_state(fresh)
    try:
        for off_value in ("", "0", "false", "False"):
            monkeypatch.setenv("BRAIN_YIELD_WEIGHTING", off_value)
            configs = [("A", "U", 1), ("B", "U", 1)]
            a_picks = sum(1 for _ in range(200) if picker.weighted_pick_config(configs)[0] == "A")
            assert 60 < a_picks < 140, f"env={off_value!r} should be off (got {a_picks}/200 A picks)"
    finally:
        dw.set_state(dw.DiversityCache())
