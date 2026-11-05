"""Pool resolution and the template-pool draw for a generation batch.

Split out of `generator/random_generator.py`, which imports these names; the
built-in builders stay in that module because tests patch them there.
"""

from generator import template_source
from generator.corpus_prior import load_corpus_prior
from generator.field_picker import get_cache
from generator.field_picker_matrix.target import get_target_category


def prepare_pools(conn):
    """Field pools, operator allowlist and template mix for one batch.

    Resolved once per batch rather than per candidate: the field pool is flat
    across datasets and the operator list comes from the database.

    Returns `(cache, field_pool, vector_fields, group_fields, known_operators,
    mix)`.
    """
    cache = get_cache()
    field_pool = [f for fields in cache.matrix_by_dataset.values() for f in fields]
    vector_fields = set(cache.vector_fields)
    group_fields = set(cache.group_fields)
    known_operators = template_source.operators_from(conn)
    mix = template_source.template_mix()
    # Per-batch like `mix`: cheap (one grouped count), and it must follow the
    # outcomes rather than a process start, or a corpus that starts yielding
    # would wait for the next restart to be weighted for it.
    load_corpus_prior(conn)
    return cache, field_pool, vector_fields, group_fields, known_operators, mix


def template_candidate(field_pool, rng, known_operators, cache, vector_fields, group_fields):
    """One expression from the mined template pool, or None.

    None means "a poor corpus" — the caller falls through to the built-ins
    rather than burning the iteration. The first slot is filled from the
    explorer's target pyramid (`target_pool`), so the template lands in the
    cell the run is targeting.
    """
    return template_source.next_expression(
        field_pool,
        rng,
        known_operators,
        target_fields=template_source.target_pool(cache, get_target_category()),
        vector_fields=vector_fields,
        group_fields=group_fields,
    )
