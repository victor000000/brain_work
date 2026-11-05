"""Logging helpers for batch submission."""

import logging

from core.log import get_file_logger

log = logging.getLogger("brain")
slog = get_file_logger("submit")


def log_batch_settings(batch_idx, expressions, settings):
    """Log all settings for debugging before submission."""
    slog.debug(
        "B%d: %d exprs %s/%s/d%d n=%s d=%d t=%s mt=%s mp=%s pa=%s nh=%s tp=%s",
        batch_idx,
        len(expressions),
        settings["region"],
        settings["universe"],
        settings["delay"],
        settings["neutralization"],
        settings["decay"],
        settings["truncation"],
        settings.get("maxTrade"),
        settings.get("maxPosition"),
        settings.get("pasteurization"),
        settings.get("nanHandling"),
        settings.get("testPeriod"),
    )


def log_batch_success(batch_idx, settings, expressions, remaining, reset_sec):
    """Log successful submission to both loggers."""
    slog.info(
        "B%d: OK %s/%s/d%d n=%s d=%d t=%s  %d exprs  rem=%s rst=%ss",
        batch_idx,
        settings["region"],
        settings["universe"],
        settings["delay"],
        settings["neutralization"],
        settings["decay"],
        settings["truncation"],
        len(expressions),
        remaining,
        reset_sec,
    )
    log.info(
        "B%d: %s/%s/d%d n=%s d=%d t=%s  %d exprs [rem=%s rst=%ss]",
        batch_idx,
        settings["region"],
        settings["universe"],
        settings["delay"],
        settings["neutralization"],
        settings["decay"],
        settings["truncation"],
        len(expressions),
        remaining,
        reset_sec,
    )
