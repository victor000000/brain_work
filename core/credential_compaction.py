"""Sanitize a stopped DuckDB 1.5.6 after verified credential-table removal.

Caller MUST hold the supervisor's exclusive flock and stop every DB user for
this entire call. This module does not authorize credential deletion: the
caller first verifies its private export and backup receipt, then drops the
credential table and closes/checkpoints the DB. No production DB is opened at
import or by tests.

COPY FROM DATABASE is the engine-supported rebuild operation:
https://duckdb.org/docs/1.5/sql/statements/copy
Sequence verification uses reopened, checkpointed start_value/SQL, NOT
last_value (whose documented semantics do not establish the drawn position):
https://duckdb.org/docs/1.5/sql/meta/duckdb_table_functions
No source nextval is evaluated. Unsupported catalog/data objects fail closed.

Byte verification covers exact UTF-8 forms of supplied nonempty strings only;
it is not forensic erasure of free filesystem blocks, snapshots, encoded or
compressed variants. A transient private hardlink keeps the dirty original
available until the installed candidate is verified; it is then unlinked.
There is no dirty-database rollback after successful cleanup, and no routine
business-database backup is created.
"""

import hashlib
import json
import os
import shutil
import stat
import tempfile
from pathlib import Path

import duckdb


class CompactionError(RuntimeError):
    """Metadata-only failure; never include SQL, values or engine diagnostics."""

    def __init__(self, message, *, rollback_path=None):
        super().__init__(message)
        self.rollback_path = str(rollback_path) if rollback_path else None


def _patterns(secret_values):
    if isinstance(secret_values, (str, bytes)):
        raise CompactionError("Supply a collection of nonempty credential strings")
    values = tuple(secret_values)
    if not values or any(not isinstance(value, str) or not value for value in values):
        raise CompactionError("Supply a collection of nonempty credential strings")
    try:
        return tuple(dict.fromkeys(value.encode("utf-8") for value in values))
    except UnicodeError:
        raise CompactionError("Credential strings must be valid UTF-8") from None


def _scan(path, patterns, chunk_size=1024 * 1024):
    if chunk_size < 1:
        raise CompactionError("Scan chunk size must be positive")
    overlap = max(map(len, patterns)) - 1
    found = set()
    tail = b""
    with open(path, "rb") as handle:
        while chunk := handle.read(chunk_size):
            block = tail + chunk
            found.update(i for i, pattern in enumerate(patterns) if pattern in block)
            tail = block[-overlap:] if overlap else b""
    return len(found)


def scan_credential_bytes(database, secret_values, *, chunk_size=1024 * 1024):
    """Return counts only; exact bytes, including matches across chunk borders."""
    patterns = _patterns(secret_values)
    return {
        "patterns_checked": len(patterns),
        "patterns_found": _scan(database, patterns, chunk_size),
        "scan_scope": "exact_utf8_bytes",
    }


def _identifier(value):
    return '"' + value.replace('"', '""') + '"'


def _literal(value):
    return "'" + str(value).replace("'", "''") + "'"


def _digest(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _identity(path):
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise CompactionError("Database must be a regular file without other hardlinks")
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def _connect():
    return duckdb.connect(
        config={
            "autoinstall_known_extensions": "false",
            "autoload_known_extensions": "false",
        }
    )


def _attach(conn, path, name, *, read_only=False):
    conn.execute(f"ATTACH {_literal(path)} AS {_identifier(name)}" + (" (READ_ONLY)" if read_only else ""))


def _rows(conn, function, columns, database):
    return conn.execute(f"SELECT {columns} FROM {function}() WHERE database_name=?", [database]).fetchall()


def _canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True, default=str, separators=(",", ":"))


def _catalogue(conn, database):
    # Identifiers/OIDs/estimated sizes are instance-specific; definitions,
    # comments, tags, constraints and effective sequence next-state are not.
    specifications = {
        "schemas": ("duckdb_schemas", "schema_name,comment,tags,internal,sql"),
        "tables": (
            "duckdb_tables",
            "schema_name,table_name,comment,tags,internal,temporary,"
            "has_primary_key,column_count,index_count,check_constraint_count,sql",
        ),
        "columns": (
            "duckdb_columns",
            "schema_name,table_name,column_name,column_index,comment,internal,"
            "column_default,is_nullable,data_type,character_maximum_length,numeric_precision,"
            "numeric_precision_radix,numeric_scale",
        ),
        "views": ("duckdb_views", "schema_name,view_name,comment,tags,internal,temporary,column_count,sql,is_bound"),
        "indexes": (
            "duckdb_indexes",
            "schema_name,index_name,table_name,comment,tags,is_unique,is_primary,expressions,sql",
        ),
        "sequences": (
            "duckdb_sequences",
            "schema_name,sequence_name,comment,tags,temporary,start_value,min_value,max_value,increment_by,cycle,sql",
        ),
        "functions": (
            "duckdb_functions",
            "schema_name,function_name,alias_of,function_type,description,"
            "comment,tags,return_type,parameters,parameter_types,varargs,macro_definition,"
            "has_side_effects,internal,examples,stability,categories",
        ),
        "constraints": (
            "duckdb_constraints",
            "schema_name,table_name,constraint_type,constraint_text,expression,"
            "constraint_column_indexes,constraint_column_names,constraint_name,"
            "referenced_table,referenced_column_names",
        ),
    }
    result = {
        name: sorted(_canonical(row) for row in _rows(conn, function, columns, database))
        for name, (function, columns) in specifications.items()
    }
    if conn.execute(
        "SELECT 1 FROM duckdb_types() WHERE database_name=? AND NOT internal LIMIT 1", [database]
    ).fetchone():
        raise CompactionError("User-defined types require a separately validated rebuild")
    for _, _, _, function_type, *_ in _rows(
        conn, "duckdb_functions", "schema_name,function_name,alias_of,function_type", database
    ):
        if function_type not in {"macro", "table_macro"}:
            raise CompactionError("Unsupported persistent function type")
    tables = _rows(conn, "duckdb_tables", "schema_name,table_name,internal,temporary", database)
    if any(internal or temporary for _, _, internal, temporary in tables):
        raise CompactionError("Internal or temporary tables require separate validation")
    views = _rows(conn, "duckdb_views", "schema_name,view_name", database)
    if any(name.lower() == "credentials" for _, name, _, _ in tables) or any(
        name.lower() == "credentials" for _, name in views
    ):
        raise CompactionError("Credential table must be removed before physical sanitization")
    # Keep this verifier conservative: JSON row hashing is validated for scalar
    # built-in types; complex/custom types need a separate typed verifier.
    for (data_type,) in _rows(conn, "duckdb_columns", "data_type", database):
        if any(marker in data_type for marker in ("[", "STRUCT(", "MAP(", "UNION(")):
            raise CompactionError("Complex column types require separate typed verification")
    return result, [(schema, name) for schema, name, _, _ in tables]


def _table_hashes(conn, database, tables):
    result = {}
    for schema, name in tables:
        relation = ".".join(map(_identifier, (database, schema, name)))
        cursor = conn.execute(f"SELECT sha256(to_json(t)) AS h FROM {relation} t ORDER BY h")
        count = 0
        digest = hashlib.sha256()
        while rows := cursor.fetchmany(8192):
            count += len(rows)
            for (row_hash,) in rows:
                digest.update(bytes.fromhex(row_hash))
        result[(schema, name)] = (count, digest.hexdigest())
    return result


def _snapshot(conn, database):
    catalogue, tables = _catalogue(conn, database)
    return catalogue, _table_hashes(conn, database, tables)


def _sync_directory(directory):
    descriptor = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def compact_if_needed(database, secret_values):
    """Rebuild only when exact supplied credential bytes remain in stopped DB.

    Caller holds the exclusive supervisor lock and all DB users are stopped.
    Requires DuckDB 1.5.6, no WAL, no credential table, single-link regular file.
    Source is attached READ_ONLY. All handles close before os.replace. Returns
    metadata only, including any dirty rollback path requiring manual cleanup.
    Pre-swap failures leave the original path intact. Candidate failures never
    authorize replacing it. A post-swap failure attempts restoration from the
    transient hardlink; if restoration/cleanup fails, CompactionError carries
    rollback_path. Do not restart writers while such a path is outstanding.
    """
    patterns = _patterns(secret_values)
    if duckdb.__version__ != "1.5.6":
        raise CompactionError("Only the validated DuckDB 1.5.6 engine is supported")
    path = Path(database).absolute()
    if path.is_symlink() or path.parent.resolve() != path.parent:
        raise CompactionError("Database path must not traverse symlinks")
    baseline = _identity(path)
    if Path(str(path) + ".wal").exists():
        raise CompactionError("Stop and checkpoint all database users before compaction; WAL exists")
    stage = None
    rollback = None
    swapped = False
    try:
        with _connect() as conn:
            _attach(conn, path, "source_db", read_only=True)
            conn.execute("SET enable_external_access=false")
            catalogue, tables = _catalogue(conn, "source_db")
        found = _scan(path, patterns)
        summary = {
            "physical_removal_verified": True,
            "rebuilt": False,
            "table_count": len(tables),
            "patterns_checked": len(patterns),
            "patterns_found_after": 0,
            "scan_scope": "exact_utf8_bytes",
            "rollback_path": None,
        }
        if not found:
            if _identity(path) != baseline:
                raise CompactionError("Database changed during maintenance")
            return summary
        # Room for a rebuilt DB, sort spill and a generous growth allowance.
        # The transient rollback is a hardlink, not a second data-file copy.
        required = max(baseline[2] * 3, 64 * 1024 * 1024)
        summary["required_free_bytes"] = required
        if shutil.disk_usage(path.parent).free < required:
            raise CompactionError("Insufficient free space for verified sanitized rebuild")
        source_digest = _digest(path)
        stage = Path(tempfile.mkdtemp(prefix=".credential-compaction-", dir=path.parent))
        candidate = stage / "sanitized.duckdb"
        with _connect() as conn:
            _attach(conn, path, "source_db", read_only=True)
            _attach(conn, candidate, "candidate_db")
            conn.execute(f"SET temp_directory={_literal(stage / 'spill')}")
            conn.execute("SET enable_external_access=false")
            before = _snapshot(conn, "source_db")
            if before[0] != catalogue:
                raise CompactionError("Source catalogue changed during maintenance")
            conn.execute("COPY FROM DATABASE source_db TO candidate_db")
            if _snapshot(conn, "candidate_db") != before:
                raise CompactionError("Candidate business data or catalogue verification failed")
            conn.execute("CHECKPOINT candidate_db")
        candidate.chmod(0o600)
        # Reopening establishes persisted sequence next-state, not transient
        # session currval. Compare definitions and state without drawing values.
        with _connect() as conn:
            _attach(conn, candidate, "candidate_db", read_only=True)
            conn.execute("SET enable_external_access=false")
            if _snapshot(conn, "candidate_db") != before:
                raise CompactionError("Reopened candidate verification failed")
            for schema, name in _rows(conn, "duckdb_views", "schema_name,view_name", "candidate_db"):
                relation = ".".join(map(_identifier, ("candidate_db", schema, name)))
                conn.execute(f"SELECT * FROM {relation} LIMIT 0")
        if Path(str(candidate) + ".wal").exists() or _scan(candidate, patterns):
            raise CompactionError("Candidate still contains credential bytes or an uncheckpointed WAL")
        candidate_digest = _digest(candidate)
        if _identity(path) != baseline or _digest(path) != source_digest or Path(str(path) + ".wal").exists():
            raise CompactionError("Source database changed before atomic replacement")
        with candidate.open("rb") as handle:
            os.fsync(handle.fileno())
        rollback = stage / "dirty-original.duckdb"
        os.link(path, rollback)
        _sync_directory(stage)
        os.replace(candidate, path)
        swapped = True
        _sync_directory(path.parent)
        if _digest(path) != candidate_digest or _scan(path, patterns):
            raise CompactionError("Installed candidate verification failed")
        # Unlink after successful install verification. Failure here must not
        # silently claim the dirty DB bytes have disappeared from all paths.
        try:
            rollback.unlink()
            rollback = None
        except OSError:
            summary.update(
                physical_removal_verified=False, rebuilt=True, rollback_path=str(rollback), cleanup_incomplete=True
            )
            return summary
        try:
            _sync_directory(stage)
        except OSError:
            summary.update(
                physical_removal_verified=False,
                rebuilt=True,
                cleanup_incomplete=True,
                cleanup_reason="rollback_unlink_durability_unverified",
            )
            return summary
        summary.update(
            rebuilt=True,
            business_row_count=sum(value[0] for value in before[1].values()),
            catalogue_sha256=hashlib.sha256(_canonical(before[0]).encode()).hexdigest(),
            verified_table_count=len(before[1]),
            sequence_count=len(before[0]["sequences"]),
        )
        return summary
    except Exception as error:
        if not swapped and rollback is not None and rollback.exists():
            try:
                rollback.unlink()
                rollback = None
            except OSError:
                raise CompactionError(
                    "Compaction failed; private dirty hardlink cleanup incomplete", rollback_path=rollback
                ) from None
        if swapped and rollback is not None and rollback.exists():
            try:
                os.replace(rollback, path)
                rollback = None
            except OSError:
                raise CompactionError(
                    "Compaction failed; dirty rollback retained; keep all writers stopped", rollback_path=rollback
                ) from None
            try:
                _sync_directory(path.parent)
            except OSError:
                raise CompactionError(
                    "Original restored; directory durability unverified; keep all writers stopped", rollback_path=path
                ) from None
        if isinstance(error, CompactionError):
            raise CompactionError(str(error)) from None
        raise CompactionError("Compaction failed safely; source retained; inspect maintenance metadata") from None
    finally:
        if stage is not None and rollback is None:
            try:
                shutil.rmtree(stage)
            except OSError:
                raise CompactionError(
                    "Private candidate cleanup incomplete; inspect retained maintenance directory", rollback_path=stage
                ) from None
