"""Template registry — cnhkmcp core + BRAIN website templates.

- 10 cnhkmcp patterns: 5 high-performing curated templates plus 5 canonical
  patterns ported from cnhkmcp 3.1.11 KB
- the BRAIN website templates: extracted from forum, learn docs, and cnhkmcp
  documentation, using only PV and options datafields
"""

from generator.templates_brain_website import TEMPLATES_BRAIN_WEBSITE
from generator.templates_cnhkmcp import TEMPLATES_CNHKMCP

ALL_TEMPLATES = TEMPLATES_CNHKMCP + TEMPLATES_BRAIN_WEBSITE

# The website registry is the source of truth for the pool convention: those
# templates take `(field_pool, rng)`, the cnhkmcp ones take two field names.
# Deciding it by inspecting a parameter *name* ("rng") silently mis-dispatches
# any template that renames the parameter, and costs an `inspect.signature`
# call per expression ever produced.
POOL_TEMPLATES = frozenset(fn for fn, _ops in TEMPLATES_BRAIN_WEBSITE)


def template_uses_pool(fn) -> bool:
    """True for pool-based templates — called `fn(field_pool, rng)`, not `fn(f1, f2)`.

    Two conventions coexist in `ALL_TEMPLATES`: cnhkmcp templates build from the
    two fields the caller picked (so pyramid targeting reaches them), while the
    website templates pick their own fields by keyword from the whole pool
    (their operands have distinct economic roles — `close` vs `volume` vs
    `sector` — that two arbitrary fields cannot supply). Callers must dispatch
    before calling: handing two field names to a pool template leaves it
    treating a field name as the RNG and raises
    `'str' object has no attribute 'choice'` inside it.

    `tests/test_templates.py` pins that `POOL_TEMPLATES` and the call
    signatures agree, so a new template cannot drift between the two.
    """
    return fn in POOL_TEMPLATES


TEMPLATE_COUNT = len(ALL_TEMPLATES)
