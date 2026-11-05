"""Read the curated collection's `###` blocks into template records.

Split out of `tools/parse_cnhkmcp_templates.py`, which re-exports
`parse_blocks`.
"""

import re


def parse_blocks(text):
    """One record per `### <name>` block that carries an expression."""
    blocks = re.split(r"^###\s+", text, flags=re.M)
    templates = []

    for chunk in blocks[1:]:
        head, _, rest = chunk.partition("\n")
        name = head.strip()

        def grab(*labels, single_line=False, _rest=rest):
            # `_rest` binds this iteration's block rather than closing over the
            # loop variable, which would otherwise be shared across iterations.
            for lab in labels:
                pat = (
                    rf"\*\*{lab}\*\*\s*:?\s*(.+)$"
                    if single_line
                    else (rf"\*\*{lab}\*\*\s*:?\s*(.+?)(?=\n\s*[\*\-]\s+\*\*|\n\s*\n|$)")
                )
                m = re.search(pat, _rest, re.S if not single_line else re.M)
                if m:
                    v = m.group(1).strip()
                    # The source wraps expressions in backticks and closes with a
                    # CJK full stop. Strip both ends: a bare .strip("`") leaves the
                    # trailing one, since the full stop sits outside it.
                    v = re.sub(r"^[`\s]+", "", v)
                    v = re.sub(r"[`\s。，、；]+$", "", v)  # noqa: RUF001 — CJK punctuation is correct here
                    v = re.sub(r"\s+", " ", v)
                    if v:
                        return v
            return ""

        expr = grab("Expression", "模板表达式", "表達式", "表达式", single_line=True)
        if not expr:
            continue

        # attribute to the nearest preceding "## From:" / "## 《" heading
        idx = text.find("### " + head)
        head_prefix = text[:idx]
        src_matches = re.findall(r"^##\s+(?:From:\s*)?(.+)$", head_prefix, re.M)
        source = src_matches[-1].strip() if src_matches else "unknown"

        templates.append(
            {
                "name": name,
                "source": source,
                "expression": expr,
                "hypothesis": grab("Hypothesis", "核心思想"),
                "settings": grab("Settings"),
                "rationale": grab("逻辑链深度解析"),
                "optimization": grab("优化方向"),
            }
        )
    return templates
