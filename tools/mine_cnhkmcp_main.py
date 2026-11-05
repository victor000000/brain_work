"""The mining pipeline: walk both corpora, filter, classify, report.

Split out of `tools/mine_cnhkmcp_templates.py`, which re-exports `main`.
Writes docs/forum/cnhkmcp_mined_templates.json.
"""

import json
import os
import re
from collections import Counter

from tools.mine_cnhkmcp_ref import EXISTING, LEARN, OUT, POSITIVE, VENDOR
from tools.mine_cnhkmcp_scan import parses, strings_from
from tools.mine_cnhkmcp_vocab import _classify, candidates_from


def main():
    found, seen, files = [], set(), []
    for base in (VENDOR, LEARN):
        for dirpath, _dirs, names in os.walk(base):
            for name in names:
                if name.endswith((".md", ".txt", ".json")):
                    files.append(os.path.join(dirpath, name))

    for fp in files:
        rel = fp.replace(VENDOR + "/", "cnhkmcp/").replace(LEARN + "/", "learn/")
        for text in strings_from(fp, rel):
            for cand in candidates_from(text):
                key = re.sub(r"\s+", "", cand)
                if key in seen or key in EXISTING:
                    continue
                seen.add(key)
                if not parses(cand):
                    continue
                pv, other = _classify(cand, POSITIVE)
                found.append(
                    {
                        "expression": cand,
                        "source_file": rel,
                        "pv_option_fields": pv,
                        "other_fields": other,
                        "fillable_from_pv_option": not other,
                    }
                )

    with open(OUT, "w", encoding="utf-8", errors="replace") as fh:
        json.dump(found, fh, ensure_ascii=False, indent=1)

    fill = [f for f in found if f["fillable_from_pv_option"]]
    print(f"scanned {len(files)} files")
    print(f"parseable expressions not already mined: {len(found)}")
    print(f"  fillable from pv/option: {len(fill)}")
    print(f"  need other/unknown data: {len(found) - len(fill)}")
    print("\nby source file (top 12):")
    for k, n in Counter(f["source_file"] for f in found).most_common(12):
        print(f"  {n:4}  {k}")
    print(f"\nfull output -> {OUT}")
