"""Process-wide write serialization for the DuckDB facade.

Split out of `core/db/compat.py`; the statement mixin and the transaction
mixin both take this lock. DuckDB runs one write transaction at a time, and
the explorer writes from its main loop while the background check thread
writes submission rows; without serialization those two connections collide
with a "write-write conflict" TransactionException. Reads take the same lock —
DuckDB connections are not thread-safe and the cost is negligible next to the
network calls around them.
"""

import re
import threading

# Statements that take the write lock. Ownership is held across an explicit
# BEGIN ... COMMIT so a transaction stays atomic against other threads.
_BEGIN_STMT = re.compile(r"^\s*BEGIN\b", re.IGNORECASE)
_END_STMT = re.compile(r"^\s*(COMMIT|ROLLBACK|END)\b", re.IGNORECASE)

_WRITE_LOCK = threading.RLock()
_LOCK_TIMEOUT = 30.0
