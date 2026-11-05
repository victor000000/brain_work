"""Refund only the exact polish reservation proved never to have simulated.

Claims remain charged across accepted requests, transport ambiguity and process
crashes. The caller must establish that the entire POST/retry history contains
no possible acceptance before passing ``definitely_unsubmitted=True``. A bare
None or a terminal budget/concurrency sentinel does not establish that fact.
"""

from core.log import get_file_logger

plog = get_file_logger("submit")


def release_unsubmitted_claim(conn, plan, *, definitely_unsubmitted):
    """Restore an unspent reservation once, without undoing any later claim.

    ``take_batch`` keeps the exact before/after row states in ``claim_receipt``.
    Compare-and-swap updates refuse to overwrite a changed or replaced row.
    The receipt is an in-process handle: settling it prevents a delayed repeat
    from refunding a newer claim that happens to have the same row values.
    An absent receipt or anything other than literal True evidence is a no-op.
    """
    if definitely_unsubmitted is not True or not plan:
        return 0
    receipt = plan.get("claim_receipt")
    if not receipt or receipt.get("settled"):
        return 0

    # Settle even a stale receipt: retrying it after the row changes back must
    # never undo a different reservation. A failure while releasing retains
    # the conservative behavior of charging the original claim.
    receipt["settled"] = True
    refunded = 0
    for state in receipt["entries"]:
        rows = conn.execute(
            """UPDATE polish_candidates SET attempts = ?, tried = ?
               WHERE alpha_id = ? AND expression = ? AND attempts = ? AND tried = ?
               RETURNING alpha_id""",
            (
                state["attempts_before"],
                state["tried_before"],
                state["alpha_id"],
                state["expression"],
                state["attempts_after"],
                state["tried_after"],
            ),
        ).fetchall()
        refunded += len(rows)
    conn.commit()
    plog.info("Released %d of %d unsubmitted polish reservation(s)", refunded, len(receipt["entries"]))
    return refunded
