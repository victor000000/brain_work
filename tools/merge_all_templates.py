#!/usr/bin/env python3
"""Merge all template sources into one comprehensive pool.

Every fillable template from the forum corpus and the two cnhkmcp corpora,
deduplicated by skeleton, written to docs/forum/forum_templates_merged.json.

The cnhkmcp files store their template text under `expression`, the forum file
under `skeleton`; both are normalised to `skeleton` here. Missing that
normalisation is why both cnhkmcp sources used to vanish silently: the dedup
read `skeleton`, saw no key, and skipped every row. Consumers read one shape.

The merged file is an inspection artifact — `generator/template_source.py`
loads the three corpora directly, so generation does not depend on this run.
"""

import json
import os

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SOURCES = (
    ("forum_templates.json", "forum"),
    ("cnhkmcp_mined_templates.json", "CNHKMCP mined"),
    ("cnhkmcp_curated_templates.json", "CNHKMCP curated"),
    ("help_center_templates.json", "help centre"),
)

OUT_PATH = os.path.join(PROJECT_DIR, "docs", "forum", "forum_templates_merged.json")


def main():
    seen = set()
    unique = []
    for name, label in SOURCES:
        path = os.path.join(PROJECT_DIR, "docs", "forum", name)
        with open(path) as fh:
            rows = json.load(fh)
        kept = 0
        for row in rows:
            if not isinstance(row, dict) or not row.get("fillable_from_pv_option"):
                continue
            skeleton = row.get("skeleton") or row.get("expression")
            if not skeleton or skeleton in seen:
                continue
            seen.add(skeleton)
            unique.append({**row, "skeleton": skeleton})
            kept += 1
        print(f"  {label}: {kept} new unique")

    with open(OUT_PATH, "w") as fh:
        json.dump(unique, fh, indent=1)

    print(f"Wrote {len(unique)} templates to {OUT_PATH}")


if __name__ == "__main__":
    main()
