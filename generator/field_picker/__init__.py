"""Pick fields by type — package layout.

State (matrix/vector/group field pools, last-loaded cache key) lives on a
module-level `FieldCache` singleton. Module functions (`load_all_fields`,
`pick_vector`, `pick_group`) and external readers go through `_cache`.

Public API:
  FieldCache, get_cache, set_cache  — singleton + cache type.
  load_all_fields(conn, region, delay, universe) — refresh pools.
  pick_vector(), pick_group()       — pick single fields by type.
"""

from generator.field_picker.cache import FieldCache, get_cache, set_cache
from generator.field_picker.loader import load_all_fields
from generator.field_picker.picks import pick_group, pick_vector

__all__ = [
    "FieldCache",
    "get_cache",
    "load_all_fields",
    "pick_group",
    "pick_vector",
    "set_cache",
]
