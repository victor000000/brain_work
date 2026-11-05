"""Seed DBs for the price/options category-filter tests.

Field rows are spread across categories that must survive the filter (pv,
option) and categories that must not (fundamental, model, news, analyst,
other). Everything sits in one region/delay/universe combo so each query can
be called with the same arguments.
"""

from core.db import connect


def make_field_conn():
    """In-memory DB with data_fields + field_blacklist, seeded across categories.

    Coverage values sit above every query's threshold, so the category filter
    is the only thing that can exclude a row.
    """
    conn = connect(":memory:")
    conn.executescript("""
        CREATE TABLE data_fields (
            id TEXT, dataset_id TEXT, category_id TEXT,
            region TEXT, delay INTEGER, universe TEXT,
            type TEXT, coverage REAL, date_coverage REAL, alpha_count INTEGER,
            description TEXT
        );
        CREATE TABLE field_blacklist (
            field_id TEXT, region TEXT, reason TEXT,
            PRIMARY KEY (field_id, region)
        );
    """)
    conn.executemany(
        "INSERT INTO data_fields VALUES (?,?,?,?,?,?,?,?,?,?,NULL)",
        [
            # MATRIX — the pool alpha expressions are built from
            ("close", "pv1", "pv", "USA", 0, "TOP3000", "MATRIX", 0.9, 0.9, 42),
            ("volume", "pv1", "pv", "USA", 0, "TOP3000", "MATRIX", 0.9, 0.9, 42),
            # Present in field_blacklist — must still be loaded (no blacklist)
            ("cap", "pv1", "pv", "USA", 0, "TOP3000", "MATRIX", 0.9, 0.9, 42),
            ("opt_iv", "option8", "option", "USA", 0, "TOP3000", "MATRIX", 0.9, 0.9, 42),
            ("assets", "fnd6", "fundamental", "USA", 0, "TOP3000", "MATRIX", 0.9, 0.9, 42),
            ("model_score", "model30", "model", "USA", 0, "TOP3000", "MATRIX", 0.9, 0.9, 42),
            ("news_sent", "news12", "news", "USA", 0, "TOP3000", "MATRIX", 0.9, 0.9, 42),
            # VECTOR
            ("vec_pv", "pv1", "pv", "USA", 0, "TOP3000", "VECTOR", 0.9, 0.9, 42),
            ("vec_an", "anl4", "analyst", "USA", 0, "TOP3000", "VECTOR", 0.9, 0.9, 42),
            # GROUP — needed by group_rank and neutralization
            ("industry", "pv30", "pv", "USA", 0, "TOP3000", "GROUP", 0.9, 0.9, 42),
            ("oth_grp", "other455", "other", "USA", 0, "TOP3000", "GROUP", 0.9, 0.9, 42),
        ],
    )
    # Label/metadata rows: MATRIX- or VECTOR-typed, but the platform gives them
    # a Group unit, so any *series* use is rejected with
    # `expected "Unit[]", found "Unit[Group:1]"`. `pv_measure` is the control —
    # same dataset, same everything but the description.
    metadata = {
        "pv149_status_5": ("MATRIX", "Status code representing current state of data/record"),
        "pv149_type_1": ("MATRIX", "Type or category of the financial instrument in the dataset"),
        "pv_measure": ("MATRIX", "Total traded volume."),
        "pv20_category": ("VECTOR", "Category classification"),
        "vec_measure": ("VECTOR", "Event volume."),
    }
    conn.executemany(
        "INSERT INTO data_fields VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        [(fid, "pv1", "pv", "USA", 0, "TOP3000", typ, 0.9, 0.9, 42, desc) for fid, (typ, desc) in metadata.items()],
    )
    # `cap` is blacklisted for USA. The pool must ignore this table entirely —
    # `close` too, mirroring CHN where 11 of 12 pv1 fields were blacklisted.
    conn.executemany(
        "INSERT INTO field_blacklist VALUES (?,?,?)",
        [
            ("cap", "USA", "event_input"),
            ("close", "USA", "lookback"),
            ("vec_pv", "USA", "group_unit"),
            ("industry", "USA", "group_unit"),
        ],
    )
    conn.commit()
    return conn


def make_target_conn(rows, fields=()):
    """In-memory DB with pyramid_targets + data_fields seeded from `rows`.

    rows: list of (region, delay, category, score) pyramid target rows.
    fields: list of (region, universe, delay, category) MATRIX datasets the
        cell's field pool can actually offer. Targets whose category has no
        matching field row are unsatisfiable and must be filtered out.
    """
    conn = connect(":memory:")
    conn.execute("""
        CREATE TABLE pyramid_targets (
            region TEXT, delay INTEGER, category TEXT, score REAL, period_start TEXT, period_end TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE data_fields (
            id TEXT, dataset_id TEXT, category_id TEXT,
            region TEXT, delay INTEGER, universe TEXT,
            type TEXT, coverage REAL, date_coverage REAL, alpha_count INTEGER,
            description TEXT
        )
    """)
    from tools.refresh_pyramid_targets.quarter import quarter_bounds

    conn.executemany("INSERT INTO pyramid_targets VALUES (?,?,?,?,?,?)", [(*row, *quarter_bounds()) for row in rows])
    conn.executemany(
        "INSERT INTO data_fields VALUES (?,?,?,?,?,?, 'MATRIX', 0.9, 0.9, 42, NULL)",
        [(f"{cat}_field", f"{cat}_ds", cat, region, delay, universe) for region, universe, delay, cat in fields],
    )
    conn.commit()
    return conn
