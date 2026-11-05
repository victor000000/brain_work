"""FieldCache — module-singleton holding the matrix/vector/group field pools."""

from __future__ import annotations


class FieldCache:
    """All field-pool state for one (region, delay, universe) load."""

    def __init__(self):
        self.matrix_by_dataset: dict = {}
        self.dataset_to_category: dict = {}
        self.datasets_by_category: dict = {}
        self.vector_fields: list = []
        self.group_fields: list = []
        self.last_loaded: tuple | None = None

    def reset(self):
        self.matrix_by_dataset = {}
        self.dataset_to_category = {}
        self.datasets_by_category = {}
        self.vector_fields = []
        self.group_fields = []
        self.last_loaded = None

    def rebuild_category_index(self):
        """Recompute datasets_by_category from dataset_to_category."""
        self.datasets_by_category = {}
        for ds, cat in self.dataset_to_category.items():
            self.datasets_by_category.setdefault(cat, []).append(ds)


_cache = FieldCache()


def get_cache() -> FieldCache:
    return _cache


def set_cache(cache: FieldCache) -> None:
    global _cache
    _cache = cache
