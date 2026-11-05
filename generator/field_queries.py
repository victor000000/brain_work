"""SQL queries for loading VECTOR and GROUP data fields.

Only price (pv) and options (option) categories are loaded — see
INCLUDE_CATEGORIES. Every field in those categories is eligible: the
field_blacklist table is no longer consulted. It had accumulated collateral
(every MATRIX field appearing in a failing expression was blacklisted, even
when incidental), which gutted small regions once price became the only pool —
CHN/TOP2000U/d0 dropped to a single usable field.

Identifier fields (isin, cusip, date, timestamp, symbol) are still excluded.
"""

from core.log import get_file_logger
from core.scope import ALLOWED_CATEGORIES, scope_sql
from generator.field_dead import cached_dead_fields

flog = get_file_logger("fields")

# Price (pv) + options (option) data only. Built from core.scope so this read
# path and the write-path guard agree on what "in scope" means — the old
# `category_id IN ('pv','option')` also rejected the platform's child
# categories (`pv-price-volume`, `option-option-analytics`), which core.scope
# deliberately accepts.
INCLUDE_CATEGORIES = "(" + ", ".join(f"'{c}'" for c in ALLOWED_CATEGORIES) + ")"
CATEGORY_FILTER = f"AND {scope_sql('category_id')}"

# Whether a MATRIX field covers enough of the universe to be worth drawing.
#
# `coverage >= 0.5` alone is what the pool and the pyramid-target scan both
# used, and it silently deletes the price pool of two whole regions. GBR and
# DEU report `coverage: 0.0` for `close` while reporting `dateCoverage: 1.0`
# and an `alphaCount` of 4,863 and 577 — the platform has simply not populated
# the metric there, and 4,863 alphas show the field is usable. Asked live on
# 2026-10-10 rather than inferred from our copy: `/data-fields` for
# GBR/TOP700/d1 returns `close` with `coverage: 0.0`, so this is the platform's
# current value and not a stale row of ours.
#
# The cost was a whole region's price templates. `close`, `vwap`, `high`,
# `low`, `open` and `adv20` were all excluded in both cells, so
# `vwap_close_spread`, `high_low_spread`, `overnight_gap`, `open_close_ratio`,
# `price_zscore_20d` and every volume template could not fire: GBR/TOP700/d1
# and DEU/TOP500/d1 were generating ~200 alphas a day out of `pattern_scores`
# and `industry_grouping_*` alone.
#
# `alpha_count > 0` is the evidence that replaces the missing metric — another
# account has already simulated the field, so it exists and returns data. It is
# deliberately narrow: it adds nothing where coverage is populated (measured
# across every configured cell, the largest effect outside GBR/DEU is +13
# fields in ASI/TOP500/d1), and a field no one has ever used still needs real
# coverage to get in.
COVERAGE_OK = "(coverage >= 0.5 OR (coverage = 0 AND alpha_count > 0))"


# Identifier and classifier fields, excluded from every field load.
#
# `isin` and `cusip` were here; `sedol` and `ticker` were not, and both reach
# the pools as MATRIX fields (`pv20_sedol`, `pv37_ticker`, `pv37_adr_ticker_di`,
# `pv20_sedol_1961`). A stored expression shows what that produces —
# `rank(group_neutralize(ts_delta(mdl313_companyname,63), sector) *
# rank(mdl313_ticker))` at **sharpe 11.18**: a signal built from a company name
# and a ticker symbol. Ranking stocks by their identifier is not a signal, it
# is a surrogate for listing order, and it clears the sharpe floor by accident.
# Measured 2026-10-11: 1,581 stored expressions carry `sedol` and 351 `ticker`.
#
# Substring rather than token matching, deliberately: `mdl230_allcap_sedol_*`
# and `fnd65_allcap_sedol_*` are keyed by SEDOL in the dataset's own naming and
# are already out of scope (model and fundamental), so refusing every name that
# spells it costs nothing in scope and cannot let a variant through.
#
# Defined once and used by both the MATRIX loader and the pyramid-target scan,
# which had a copy each — the drift this file has already been bitten by twice.
IDENTIFIER_EXCLUDES = (
    "isin",
    "cusip",
    "sedol",
    "ticker",
    "date",
    "timestamp",
    "symbol",
)


def identifier_filter(alias: str = "") -> str:
    """`AND id NOT LIKE ...` for every identifier name, for SQL splicing."""
    col = f"{alias}.id" if alias else "id"
    return " AND ".join(f"{col} NOT LIKE '%{name}%'" for name in IDENTIFIER_EXCLUDES)


# Fields the platform describes as a *label* rather than a measurement.
#
# The platform's `description` column says plainly what these are — "Integer
# label indicating membership in one of 2 robust, return-based industry
# clusters", "Categorical cluster ID assigning each stock to one of 10
# clusters", "Statistical industry cluster assignment". Ranking stocks by
# cluster number is not a signal, and 6,396 stored expressions do it, among them
# the three highest-sharpe CHN alphas. Measured 2026-10-11: 20 of 1,374
# all-time gate-passers use one.
#
# **Classified by description, not by name, because the name cannot decide.**
# `factor3_grouping2_score_top600` is an integer label while
# `factor2_grouping2_score_top100_eas513` is "a score for the second factor" —
# the same naming family holds both. The description rule is also a strict
# superset of the name rule: 1,713 fields against 897, with zero name-matched
# fields it misses.
#
# Applied to every pool that feeds a *series* position — the MATRIX and VECTOR
# loaders. `query_group_fields` is a separate query and does not apply it, so a
# label stays available where it belongs — as a group argument to `group_*` and
# `bucket`, which is the correct use of a partition and the reason this is a
# pool filter rather than a type check.
#
# The two metadata phrases were added 2026-10-11 on direct evidence, and they
# are the highest-cost exclusion measured so far. `pv149_status_5` ("Status code
# representing current state of data/record, e.g., valid, missing, suspended")
# and `pv149_type_1` ("Type or category of the financial instrument") are
# MATRIX-typed in `data_fields` but carry a **Group unit** on the platform, so
# every expression that uses one as a series is rejected —
# `Incompatible unit for input of "rank" at index 0, expected "Unit[]", found
# "Unit[Group:1]"`, recorded against both fields in `sim_errors`.
#
# The cost is not the 501 child simulations they consumed since 2026-10-01; it
# is the batch. **Of the 374 ten-expression batches containing one of the two,
# 373 failed all ten children (99.7%), against 87 of 4,286 (2.0%) without** —
# one unsimulatable expression fails the whole multi-sim, so each draw of one of
# these fields spends ten simulations and returns nothing. Neither field has
# produced a single alpha in 219,274 stored results, while pv149's five other
# fields (`pv149_dld_*`) complete normally: 20 alphas from 24 uses. The rule is
# about the field, not its dataset.
#
# `COALESCE` because a NULL description makes `NOT (...)` NULL, which would
# silently drop every field whose description the download did not populate.
# Native JjPG9WAm (2026-10-20) ranked pv20_country_code_1965 as a
# conditioning series. Its exact native description is "ISO country code for
# the data." MATRIX typing does not make an ISO country identifier a measured
# quantity. Match that description prefix, rather than every mention of a
# country, so country exposure/return measurements remain usable. GROUP inputs
# continue through their separate loader.
# Native IND YPx70EEJ used pv13_revere_country, described simply as
# "Country code". Match that exact label (with terminal punctuation),
# preserving measurements that merely mention country codes.
# Native HKG mLY6dWzx ranked pv13_revere_city ("City code") on2026-10-21.
# Match the complete metadata description, preserving city-related measurements.
# pv13_revere_level describes taxonomy depth, not a measured price/volume level.
# Keep this semantic match exact so price levels and sector returns survive.
LABEL_DESCRIPTION_SQL = (
    "(COALESCE(lower(description), '') LIKE '%cluster%'"
    " OR COALESCE(lower(description), '') LIKE '%grouping%'"
    " OR COALESCE(lower(description), '') LIKE '%label%'"
    " OR COALESCE(lower(description), '') LIKE '%categorical%'"
    " OR COALESCE(lower(description), '') LIKE '%group assignment%'"
    " OR COALESCE(lower(description), '') LIKE '%classification%'"
    " OR COALESCE(lower(description), '') LIKE '%status code%'"
    " OR COALESCE(lower(trim(description)), '') LIKE 'iso country code%'"
    " OR COALESCE(lower(trim(description)), '') LIKE 'currency code for %'"
    " OR COALESCE(lower(trim(description)), '') LIKE 'currency code of %'"
    " OR COALESCE(lower(trim(description)), '') LIKE 'currency code used %'"
    " OR COALESCE(lower(trim(description)), '') LIKE 'iso currency code for %'"
    " OR COALESCE(lower(trim(description)), '') LIKE 'iso currency code indicating %'"
    " OR COALESCE(rtrim(lower(trim(description)), '.'), '') = 'currency code'"
    " OR COALESCE(rtrim(lower(trim(description)), '.'), '') = 'the currency in which the equity security is traded or settled'"
    " OR COALESCE(rtrim(lower(trim(description)), '.'), '') = 'country code'"
    " OR COALESCE(rtrim(lower(trim(description)), '.'), '') = 'city code'"
    " OR COALESCE(rtrim(lower(trim(description)), '.'), '') = 'level of the sector within the hierarchy'"
    " OR COALESCE(lower(description), '') LIKE '%type or category%')"
)


def not_label_filter() -> str:
    """`AND NOT (...)` for the label predicate, for SQL splicing."""
    return f"AND NOT {LABEL_DESCRIPTION_SQL}"


def query_vector_fields(conn, region, delay, universe):
    """Load VECTOR field IDs.

    Carries the label filter too. VECTOR fields are read as series (event
    inputs), never as partitions, so a label here has no correct use — and the
    loader had none of the filter until 2026-10-11, which let the same
    Group-unit class through a second door: `pv20_category` ("Category
    classification"), `pv48_dynamic_es_cur` ("Pre-change economic sector
    classification code") and 48 more.
    """
    rows = conn.execute(
        f"""
        SELECT id FROM data_fields
        WHERE region=? AND delay=? AND universe=? AND type='VECTOR'
          AND coverage >= 0.3
          {CATEGORY_FILTER}
          {not_label_filter()}
        ORDER BY RANDOM() LIMIT 100
    """,
        (region, delay, universe),
    ).fetchall()
    dead = cached_dead_fields(conn)
    result = [row[0] for row in rows if row[0] not in dead]
    flog.debug("VECTOR %s/%s/d%d: %d fields", region, universe, delay, len(result))
    return result


def query_group_fields(conn, region, delay, universe):
    """Load GROUP field IDs."""
    rows = conn.execute(
        f"""
        SELECT id FROM data_fields
        WHERE region=? AND delay=? AND universe=? AND type='GROUP'
          {CATEGORY_FILTER}
        ORDER BY RANDOM() LIMIT 100
    """,
        (region, delay, universe),
    ).fetchall()
    result = [row[0] for row in rows]
    flog.debug("GROUP %s/%s/d%d: %d fields", region, universe, delay, len(result))
    return result
