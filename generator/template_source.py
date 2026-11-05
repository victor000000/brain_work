"""Forum-mined template pool for expression generation.

Loads the skeletons mined from the community forum, keeps the ones that can
actually produce an expression over the current pv/option field pool, and
fills them at generation time.

The corpus is noisy — user-written text, ~20% of it prose fragments and
placeholder syntax — so the pool is filtered twice before use: once on load
(slot check, operand check, operator allowlist) and once per expression
(py-fastplus plus the operator allowlist). A generated expression that fails
validation is discarded rather than returned.

Disabled with `BRAIN_TEMPLATE_MIX=0`.

The pieces live in `template_source_corpus` (paths, labels, mix setting),
`template_source_pool` (the cached load) and `template_source_pick` (per-
expression selection); they are re-exported here so
`from generator import template_source as ts` keeps resolving.
"""

from __future__ import annotations

from generator.template_fill import (  # noqa: F401
    FILL_ATTEMPTS,
    clean_skeleton,
    fill_skeleton,
    filled_expression_problem,
    is_usable,
    slot_count,
)
from generator.template_source_corpus import (  # noqa: F401
    _CORPUS_BY_FILE,
    DEFAULT_MIX,
    PROJECT_DIR,
    TEMPLATE_PATHS,
    _corpus_label,
    _normalise,
    template_mix,
)
from generator.template_source_pick import next_expression, operators_from, target_pool  # noqa: F401
from generator.template_source_pool import load_pool, reset_cache  # noqa: F401
from generator.validate import load_operator_names  # noqa: F401
from generator.weighted_selection import record_expr_template  # noqa: F401
