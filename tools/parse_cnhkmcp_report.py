"""Write the curated JSON and print the fillability summary.

Split out of `tools/parse_cnhkmcp_templates.py`, which re-exports
`write_and_report`.
"""

import json
from collections import Counter


def write_and_report(uniq, out) -> None:
    with open(out, "w") as fh:
        json.dump(uniq, fh, ensure_ascii=False, indent=1)

    fill = [t for t in uniq if t["fillable_from_pv_option"]]
    print(f"templates parsed        : {len(uniq)}")
    print(f"  fillable from pv/option: {len(fill)}")
    print(f"  need other data        : {len(uniq) - len(fill)}")
    print()
    print("=== pv/option-fillable templates ===")
    for t in fill:
        print(f"  {t['name'][:60]}")
        print(f"     {t['expression'][:120]}")
    print()
    print("=== sources ===")
    for k, v in Counter(t["source"][:52] for t in uniq).most_common():
        print(f"  {v:4}  {k}")
