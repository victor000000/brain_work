"""Read-only database access shared by reports, with explicit snapshot fallback."""

import re
from datetime import UTC, datetime
from pathlib import Path

from core.db import DB_PATH, OperationalError, connect_for_reading


def _backups(path):
    prefix = path.name + ".bak-"
    pattern = re.compile(re.escape(prefix) + r"(\d{8}T(?:\d{6}|\d{4})Z)(?:[-.].*)?$")
    found = []
    for candidate in path.parent.glob(prefix + "*"):
        match = pattern.fullmatch(candidate.name)
        if not match or not candidate.is_file() or candidate.name.endswith((".wal", ".tmp")):
            continue
        stamp = match[1]
        fmt = "%Y%m%dT%H%M%SZ" if len(stamp) == 16 else "%Y%m%dT%H%MZ"
        try:
            instant = datetime.strptime(stamp, fmt).replace(tzinfo=UTC)
        except ValueError:
            continue
        found.append((instant, candidate.name, candidate))
    return [candidate for _, _, candidate in sorted(found, reverse=True)]


def open_report_db(path=None):
    """Return (read-only connection, source path); the caller closes the connection.

    Only the live default falls back. An explicitly selected snapshot must be
    readable itself. Checkpoints are ordered by their UTC filename timestamp;
    copy tools can preserve old mtimes, and minute/second stamps sort differently.
    """
    source = Path(path or DB_PATH)
    try:
        return connect_for_reading(str(source)), str(source)
    except OperationalError as error:
        if source.resolve() != Path(DB_PATH).resolve():
            raise
        for backup in _backups(source):
            try:
                conn = connect_for_reading(str(backup))
            except OperationalError:
                continue
            reason = str(error).splitlines()[0][:120]
            print(f"(live database unavailable: {reason}; using snapshot {backup.name})")
            return conn, str(backup)
        raise OperationalError("live database unavailable and no readable timestamped backup exists") from error
