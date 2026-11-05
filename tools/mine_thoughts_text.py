"""The prose window that a mined expression line is reported with.

Split out of `tools/mine_template_thoughts.py`, which re-exports these names.
"""

import re

# Room for a claim, its numbers and the expression it is about. 600 was not
# enough: 1,639 of 11,091 stored thoughts hit the cap exactly (the 90th
# percentile is the cap itself), so a tenth of the corpus ends mid-sentence.
# The cost is concrete — the GLB dual-bucket post (Sharpe 6.24, PC 0.79 →
# 0.68, "15 ablations") stores its quantities and no expression, which is why
# that recipe could not be built from the corpus on 2026-10-12. Nothing in the
# generator reads this file, so the extra text costs disk only.
MAX_THOUGHT_CHARS = 1600
# Window used when a document has no blank-line paragraphs (a code dump).
CONTEXT_LINES = 8

# The corpus line may carry a label; the miner strips it before slotting.
_LABEL = re.compile(r"^(alpha|expression|expr|表达式|信号|signal)\s*[:：=]\s*", re.I)  # noqa: RUF001


def paragraph_around(text: str, line: str) -> str | None:
    """The blank-line block containing `line`, else a ±CONTEXT_LINES window."""
    idx = text.find(line)
    if idx == -1:
        return None
    start = text.rfind("\n\n", 0, idx)
    end = text.find("\n\n", idx + len(line))
    block = text[(start + 2) if start != -1 else 0 : end if end != -1 else len(text)].strip()
    if (start == -1 and end == -1) or block == line.strip():
        # No blank-line paragraphs at all (a code dump), or the expression is a
        # paragraph of its own — the neighbouring lines are the context. Without
        # this a long one-block document returns its first 600 characters for
        # every line it holds, text that may never mention the line at all.
        lines = text.split("\n")
        pos = next((i for i, ln in enumerate(lines) if ln.strip() == line.strip()), None)
        if pos is not None:
            block = "\n".join(lines[max(0, pos - CONTEXT_LINES) : pos + CONTEXT_LINES + 1]).strip()
    at = block.find(line.strip())
    if at >= MAX_THOUGHT_CHARS:
        # Long neighbouring lines push the line past the cut; start the window
        # so the text still contains the expression it is attached to.
        block = block[max(0, at - MAX_THOUGHT_CHARS // 2) :]
    return block[:MAX_THOUGHT_CHARS] or None
