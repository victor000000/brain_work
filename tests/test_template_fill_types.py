"""Field-type blindness: MATRIX fields in VECTOR/GROUP positions."""

import random

from generator.template_fill import filled_expression_problem, generate_from_templates, type_violation
from tests.test_template_fill_helpers import OPS

MATRIX = ["close", "volume"]
VECTOR = ["vec_sent"]
GROUP = ["industry", "sector"]


def test_type_violation_rejects_matrix_in_vec_call():
    assert type_violation("vec_avg(close)", MATRIX, VECTOR, GROUP) is not None
    assert type_violation("ts_mean(vec_avg(close),5)", MATRIX, VECTOR, GROUP) is not None


def test_type_violation_rejects_matrix_in_group_argument():
    assert type_violation("group_rank(close,volume)", MATRIX, VECTOR, GROUP) is not None
    # group_mean takes (x, weight, group) — the group is the third positional.
    assert type_violation("group_mean(close,1,volume)", MATRIX, VECTOR, GROUP) is not None
    # Unlisted group_* operators fall back to the last positional argument.
    assert type_violation("group_bucket(close,volume)", MATRIX, VECTOR, GROUP) is not None


def test_an_ambiguous_field_does_not_satisfy_a_group_argument():
    """A field recorded as BOTH GROUP and MATRIX is read as a series by the
    platform, so it must not fill a group slot.

    1,277 fields are GROUP+MATRIX, and structurally rather than by noise: the
    same id is a different type in a different universe (`top2000_factor8_value`
    is GROUP in TOP3000 and MATRIX in ILLIQUID_MINVOL1M), while the pools are
    built globally, so the union of those answers is "both" — and "both" used to
    read as a valid group. `densify` on one is the recorded failure, and it is
    the whole path: `densify(` appears in 0 of 214,359 stored alphas.
    """
    matrix = [*MATRIX, "top2000_factor8_value"]
    groups = [*GROUP, "top2000_factor8_value"]

    assert type_violation("densify(top2000_factor8_value)", matrix, VECTOR, groups) is not None
    assert type_violation("group_neutralize(close,top2000_factor8_value)", matrix, VECTOR, groups) is not None
    # ...while an unambiguous group in the same pools still fills the slot.
    assert type_violation("densify(sector)", matrix, VECTOR, groups) is None


def test_type_violation_accepts_correct_types():
    assert type_violation("vec_avg(vec_sent)", MATRIX, VECTOR, GROUP) is None
    assert type_violation("group_rank(close,industry)", MATRIX, VECTOR, GROUP) is None
    assert type_violation("group_mean(close,1,sector)", MATRIX, VECTOR, GROUP) is None
    assert type_violation("rank(close)", MATRIX, VECTOR, GROUP) is None


def test_type_violation_rejects_a_group_name_where_a_series_is_wanted():
    """The mirror of the group check: a grouping name is not a data series.

    Mined skeletons carry literals like `ts_corr({f}, market, 20)`, which reads
    `market` as a data series. Both `field_violation` and the operator
    allowlist let it through — GROUP_NAMES are deliberately not dataset fields —
    and the platform answers `Incompatible unit for input of "ts_corr" at index
    1, expected "Unit[]", found "Unit[Group:1]"`. Observed live 2026-10-06.
    """
    problem = type_violation("ts_rank(ts_corr(x, market, 20),5)", MATRIX, VECTOR, GROUP)
    assert problem is not None and "market" in problem
    assert type_violation("rank(industry)", MATRIX, VECTOR, GROUP) is not None


def test_type_violation_rejects_a_group_field_where_a_series_is_wanted():
    """A dataset field typed GROUP is valid only in a group slot.

    `group_name_as_series` covers the built-in names, but a dataset grouping
    such as `technology_pca_factor2_grouping5` is a *known field*, so
    `field_violation` lets it land anywhere. Observed live 2026-10-06:
    `ts_arg_max(technology_pca_factor2_grouping5,3)==0` came back
    `Incompatible unit for input of "ts_arg_max" at index 0, expected
    "Unit[]", found "Unit[Group:1]"` — a simulation spent for nothing.
    """
    grouping = {"technology_pca_factor2_grouping5"}
    problem = type_violation("ts_arg_max(technology_pca_factor2_grouping5,3)==0", MATRIX, VECTOR, grouping)
    assert problem is not None and "technology_pca_factor2_grouping5" in problem
    assert type_violation("ts_corr(close,technology_pca_factor2_grouping5,20)", MATRIX, VECTOR, grouping) is not None
    # group_mean(x, weight, group): the weight is a series, not a group.
    assert (
        type_violation("group_mean(close,technology_pca_factor2_grouping5,sector)", MATRIX, VECTOR, grouping)
        is not None
    )
    # The same field in the group slot it belongs in is exactly right.
    assert type_violation("group_rank(close,technology_pca_factor2_grouping5)", MATRIX, VECTOR, grouping) is None


def test_a_group_name_in_its_own_position_is_still_fine():
    """The new check must not reject the legitimate uses it sits next to."""
    assert type_violation("group_zscore(-ts_delta(close,2),sector)", MATRIX, VECTOR, GROUP) is None
    assert (
        type_violation("group_neutralize(close, bucket(rank(volume), range='0,1,0.1'))", MATRIX, VECTOR, GROUP) is None
    )


def test_filled_expression_problem_includes_type_checks():
    assert filled_expression_problem("vec_avg(close)", MATRIX, OPS, VECTOR, GROUP) is not None


def test_generate_from_templates_fills_a_vec_slot_from_the_vector_pool():
    """A `vec_*` slot draws from VECTOR, so the skeleton is usable.

    It used to draw from the MATRIX pool and produce nothing, which is what
    `template_fill_types` documented as a known limitation: 110 of the live
    pool's 569 skeletons call a group- or vector-taking operator, and the ones
    whose every slot was mistyped could never render at all.
    """
    out = generate_from_templates(
        [{"skeleton": "vec_avg({f})"}],
        MATRIX,
        count=3,
        rng=random.Random(6),
        known_operators=OPS,
        vector_fields=VECTOR,
        group_fields=GROUP,
    )
    assert out == ["vec_avg(vec_sent)"]


def test_generate_from_templates_drops_a_typed_slot_with_no_pool():
    """With no VECTOR pool the slot falls back to MATRIX and is rejected.

    The fallback is deliberate: an unsatisfiable fill must degrade to the old
    behaviour rather than raise, so a caller that passes no typed pools gets
    exactly what it got before role-aware filling existed.
    """
    out = generate_from_templates(
        [{"skeleton": "vec_avg({f})"}],
        MATRIX,
        count=3,
        rng=random.Random(6),
        known_operators=OPS,
        vector_fields=None,
        group_fields=None,
    )
    assert out == []


def test_generate_from_templates_fills_a_group_slot_from_the_group_pool():
    """`group_neutralize({f},{f})` was unreachable: both slots drew MATRIX."""
    out = generate_from_templates(
        [{"skeleton": "group_neutralize({f},{f})"}],
        MATRIX,
        count=4,
        rng=random.Random(7),
        known_operators=OPS,
        vector_fields=VECTOR,
        group_fields=GROUP,
    )
    assert out, "the shape renders once its group slot draws a GROUP field"
    assert all(e.startswith("group_neutralize(") for e in out)
    for e in out:
        series, _, group = e[len("group_neutralize(") : -1].partition(",")
        assert series in MATRIX
        assert group in GROUP, f"group slot filled from the wrong pool: {e}"


def test_type_violation_rejects_matrix_in_densify():
    """`densify` takes a GROUP and its name does not say so.

    The argument went unchecked because the walk keyed on the `vec_`/`group_`
    prefixes — the one recorded failure is a `proven` skeleton that filled
    `densify` with a MATRIX group-flavoured field.
    """
    assert type_violation("densify(close)", MATRIX, VECTOR, GROUP) is not None
    assert type_violation("group_zscore(ts_av_diff(close,66),densify(volume))", MATRIX, VECTOR, GROUP) is not None


def test_densify_accepts_a_real_group():
    """A group field or a built-in grouping name is exactly right."""
    assert type_violation("group_neutralize(close,densify(industry))", MATRIX, VECTOR, GROUP) is None
    assert type_violation("densify(sector)", MATRIX, VECTOR, GROUP) is None
    # A compound argument may legitimately produce a group; left to the platform.
    assert type_violation("densify(bucket(rank(close), range='0,1,0.1'))", MATRIX, VECTOR, GROUP) is None
