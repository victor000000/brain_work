"""Registry invariants: the template list, its pool flag and uniqueness."""

from generator.registry import ALL_TEMPLATES, TEMPLATE_COUNT, template_uses_pool


def test_template_count():
    """Registry holds the cnhkmcp curated set plus the website templates."""
    assert len(ALL_TEMPLATES) == TEMPLATE_COUNT
    assert TEMPLATE_COUNT >= 5


def test_pool_convention_matches_the_website_registry():
    """`template_uses_pool` reads the registry list, so the two must not drift.

    A template that gains or loses its `rng` parameter (or moves between the
    lists) would otherwise be called with the other convention and fail inside
    the template.
    """
    import inspect

    by_signature = {fn for fn, _ops in ALL_TEMPLATES if "rng" in inspect.signature(fn).parameters}
    by_registry = {fn for fn, _ops in ALL_TEMPLATES if template_uses_pool(fn)}
    assert by_registry == by_signature


def test_no_duplicate_template_functions():
    """No template function appears twice in the registry."""
    fns = [fn for fn, _ops in ALL_TEMPLATES]
    assert len(fns) == len(set(id(fn) for fn in fns)), "Duplicate template function in registry"
