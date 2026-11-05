"""Per-dimension weight cache shared across the diversity-weighting modules."""


class DiversityCache:
    """Holds the count- and yield-based weight maps."""

    def __init__(self):
        self.region_config_weights: dict = {}
        self.region_config_yield_weights: dict = {}
        self.neutralization_weights: dict = {}
        self.decay_weights: dict = {}
        self.truncation_weights: dict = {}
        self.test_period_weights: dict = {}
        # Wall-clock timestamp of the most recent successful load.
        # Used by `load_diversity_weights` to skip redundant DB reloads.
        self.loaded_at: float = 0.0

    def reset(self):
        self.region_config_weights = {}
        self.region_config_yield_weights = {}
        self.neutralization_weights = {}
        self.decay_weights = {}
        self.truncation_weights = {}
        self.test_period_weights = {}
        self.loaded_at = 0.0
