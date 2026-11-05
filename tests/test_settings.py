"""Test settings factory and constraints."""

from core.constraints import NO_MAX_POSITION_REGIONS, NO_STATISTICAL_REGIONS
from runner.settings_factory import make_settings


def test_make_settings_basic():
    s = make_settings("USA", "TOP3000", 1)
    assert s["region"] == "USA"
    assert s["universe"] == "TOP3000"
    assert s["delay"] == 1
    assert s["instrumentType"] == "EQUITY"
    assert s["language"] == "FASTEXPR"
    assert s["pasteurization"] == "ON"
    assert s["unitHandling"] == "VERIFY"


def test_settings_has_required_keys():
    s = make_settings("EUR", "TOP2500", 1)
    for key in ["decay", "neutralization", "truncation", "maxTrade", "maxPosition", "testPeriod"]:
        assert key in s


def test_statistical_neutralization_excluded():
    """CHN should never get STATISTICAL neutralization."""
    assert "CHN" in NO_STATISTICAL_REGIONS
    for _ in range(50):
        s = make_settings("CHN", "TOP2000U", 0)
        assert s["neutralization"] != "STATISTICAL"


def test_no_max_position_regions():
    for region in NO_MAX_POSITION_REGIONS:
        for _ in range(20):
            s = make_settings(region, "TOP3000", 1)
            assert s["maxPosition"] == "OFF"


def test_make_settings_accepts_pre_picked_neutralization(monkeypatch):
    """When neutralization is supplied, make_settings uses it instead of auto-picking."""
    from runner.settings_factory import make_settings

    settings = make_settings("USA", "TOP3000", 1, neutralization="MARKET")
    assert settings["neutralization"] == "MARKET"


def test_make_settings_auto_picks_when_neutralization_none():
    """Backward-compat: omit neutralization → factory auto-picks (same as before)."""
    from runner.settings_factory import make_settings

    settings = make_settings("USA", "TOP3000", 1)
    # auto-picked from pool; just verify a non-None value was chosen.
    assert settings["neutralization"]


def test_pick_neutralization_is_public():
    """The function is exposed publicly so the explorer can call it directly."""
    from runner.settings_factory import pick_neutralization

    n = pick_neutralization("USA")
    assert isinstance(n, str)
