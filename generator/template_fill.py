"""Runtime substitution of pv/option fields into mined template skeletons.

Skeletons come from the forum corpus (`docs/forum/forum_templates.json`), where
datafields were normalised to `{f}` slots. They are user-written, so they are
noisy: some are prose fragments, some use placeholder identifiers (`x`, `d`,
`A`) that parse fine but are not fields, and the corpus is only ~18% valid
after substitution.

So nothing here trusts the source. A skeleton is usable only if it either has
slots to fill or reads at least one field we hold (a slotless skeleton that
reads nothing is a constant like `ts_av_diff(185,5)`), its shape parses with
every slot stood in by a placeholder (`skeleton_shape_problem` — ~70% of the
loadable corpus is prose that only failed after filling), and every expression
produced is validated with py-fastplus before it is returned.

Slots draw independently when no complete matching source example establishes
their identities. When it does, repeated references share one chosen field:
`(close-ts_mean(close,20))/ts_std_dev(close,20)` stays a one-field z-score.
Different source variables (such as condition and signal in trade_when) still
draw independently. No identity is guessed from anonymous placeholders alone.

Every value token is checked against the field pool — slots do not launder a
skeleton's literals: `-ts_backfill(zscore({f}/sales),65)*(...)` fills and
validates, and spends a simulation on `sales`, a fundamental field the
pv/option restriction put out of reach.

The pieces live in siblings: `template_fill_tokens` (slots and value tokens),
`template_fill_usable` (the load-time gate), `template_fill_clean` (prose and
assignment recovery), `template_fill_args` (call-site argument scanning),
`template_fill_types` (operator-argument type contracts) and
`template_fill_slots` (filling and validated generation). They are re-exported
here so `from generator.template_fill import ...` keeps resolving.
"""

from __future__ import annotations

from generator.template_fill_args import (  # noqa: F401
    _CALL_SITE_RE,
    _call_arguments,
    _matching_paren,
    _skip_string,
    _split_args,
)
from generator.template_fill_clean import (  # noqa: F401
    _ASSIGNMENT,
    _CALL_START,
    _TRAILING_OPERATORS,
    _balanced_candidates,
    clean_skeleton,
)
from generator.template_fill_slots import (  # noqa: F401
    FILL_ATTEMPTS,
    fill_skeleton,
    generate_from_templates,
)
from generator.template_fill_tokens import (  # noqa: F401
    _VALUE_TOKEN_RE,
    GROUP_NAMES,
    KEYWORDS,
    SLOT,
    _value_tokens,
    field_violation,
    slot_count,
    unknown_field_tokens,
)
from generator.template_fill_types import (  # noqa: F401
    GROUP_ARG_INDEXES,
    _positional_index,
    densify_slot_problem,
    filled_expression_problem,
    type_violation,
)
from generator.template_fill_usable import (  # noqa: F401
    _ADJACENT_SLOTS,
    _SLOT_STANDIN,
    is_usable,
    skeleton_shape_problem,
)
