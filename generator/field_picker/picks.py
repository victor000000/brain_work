"""Pick a single VECTOR or GROUP field from the cache."""

import random

from core.log import get_file_logger
from generator.field_picker.cache import get_cache

glog = get_file_logger("generator")


def pick_vector():
    """Pick one VECTOR field. Returns None if empty."""
    cache = get_cache()
    if cache.vector_fields:
        return random.choice(cache.vector_fields)
    glog.debug("No VECTOR fields available")
    return None


def pick_group():
    """Pick one GROUP data field. Returns None if empty."""
    cache = get_cache()
    if cache.group_fields:
        return random.choice(cache.group_fields)
    glog.debug("No GROUP fields available")
    return None
