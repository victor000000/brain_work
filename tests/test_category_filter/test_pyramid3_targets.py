"""Pyramid targeting must never aim at a category the field pool can't satisfy.

pyramid3 picks the target category *before* fields load, so a target outside
the allowed categories wins the score-weighted draw and then silently falls
through to legacy picking (field_picker_matrix/pick.py). The target filter and
the field filter have to agree.
"""

from generator.diversity_picker.pyramid3 import FALLBACK_CATEGORY, pyramid3_weighted_pick
from tests.test_category_filter.conftest import make_target_conn

CONFIGS = [("USA", "TOP3000", 0)]

TARGETS = [
    ("USA", 0, "pv", 5.0),
    ("USA", 0, "option", 4.0),
    ("USA", 0, "fundamental", 3.0),
    ("USA", 0, "news", 2.0),
    ("USA", 0, "socialmedia", 1.0),
]

PV_FIELD = [("USA", "TOP3000", 0, "pv")]
OPTION_FIELD = [("USA", "TOP3000", 0, "option")]


def test_pyramid3_never_targets_an_unreachable_category():
    """200 draws: with these weights the excluded categories would appear fast."""
    conn = make_target_conn(TARGETS, fields=PV_FIELD)
    seen = {
        category for _ in range(200) for _, category in [pyramid3_weighted_pick(conn, CONFIGS)] if category is not None
    }
    assert seen, "picker returned no category at all"
    assert seen <= {"pv", "option"}, f"targeted unreachable categories: {seen - {'pv', 'option'}}"


def test_pyramid3_drops_target_with_no_matching_fields():
    """option is in scope, but the cell has no option MATRIX field -> pv only."""
    conn = make_target_conn([("USA", 0, "option", 9.0), ("USA", 0, "pv", 1.0)], fields=PV_FIELD)
    categories = {pyramid3_weighted_pick(conn, CONFIGS)[1] for _ in range(50)}
    assert categories == {"pv"}


def test_pyramid3_still_targets_option_when_it_is_the_only_allowed_row():
    """The filter must keep option, not just drop to pv."""
    conn = make_target_conn(
        [("USA", 0, "option", 1.0), ("USA", 0, "news", 9.0)],
        fields=OPTION_FIELD,
    )
    categories = {pyramid3_weighted_pick(conn, CONFIGS)[1] for _ in range(50)}
    assert categories == {"option"}


def test_pyramid3_falls_back_when_no_allowed_target_exists():
    """No pv/option rows -> (config, pv) fallback, not an excluded category."""
    conn = make_target_conn(
        [("USA", 0, "news", 9.0), ("USA", 0, "fundamental", 5.0)],
        fields=PV_FIELD,
    )
    config, category = pyramid3_weighted_pick(conn, CONFIGS)
    assert category == FALLBACK_CATEGORY == "pv"
    assert config == CONFIGS[0]


def test_pyramid3_skips_satisfiability_filter_without_field_table():
    """Legacy schemas without data_fields keep the old in-scope filtering."""
    from core.db import connect

    conn = connect(":memory:")
    from tools.refresh_pyramid_targets.quarter import quarter_bounds

    conn.execute(
        "CREATE TABLE pyramid_targets "
        "(region TEXT, delay INTEGER, category TEXT, score REAL, period_start TEXT, period_end TEXT)"
    )
    conn.execute("INSERT INTO pyramid_targets VALUES ('USA', 0, 'option', 9.0, ?, ?)", quarter_bounds())
    categories = {pyramid3_weighted_pick(conn, CONFIGS)[1] for _ in range(20)}
    assert categories == {"option"}
