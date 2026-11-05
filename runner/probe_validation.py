"""Validate a planned probe against the same field/type gates as generation."""

import math

from core.constraints import ALLOWED_NEUT_BY_REGION, MAX_TRADE_POSITION_CONFLICT, NO_MAX_POSITION_REGIONS
from core.regions import REGION_CONFIGS
from generator.field_validation_pools import validation_pools as target_pools
from generator.operator_count import operator_count
from generator.template_fill import filled_expression_problem
from generator.template_fill_tokens import GROUP_NAMES, _value_tokens
from generator.validate import load_operator_names, parse_error
from runner.probe_bindings import validation_expressions
from runner.python_probe_source import validate_python_source


def validate_probe(conn, expressions, settings, template_tags):
    """Raise on an invalid payload before it can consume a simulation."""
    if not isinstance(expressions, list) or not 1 <= len(expressions) <= 10:
        raise ValueError("a probe must contain 1 to 10 expressions")
    if any(not isinstance(expr, str) or not expr.strip() for expr in expressions):
        raise ValueError("probe expressions must be nonempty strings")
    if len(set(expressions)) != len(expressions):
        raise ValueError("duplicate expression in probe batch")
    if not isinstance(template_tags, list) or len(template_tags) != len(expressions):
        raise ValueError("each probe expression needs a template tag")
    if any(not isinstance(tag, str) or not tag.strip() for tag in template_tags):
        raise ValueError("probe template tags must be nonempty strings")
    if not isinstance(settings, dict):
        raise ValueError("probe settings must be an object")
    region, universe, delay = (settings.get(name) for name in ("region", "universe", "delay"))
    if type(delay) is not int or (region, universe, delay) not in REGION_CONFIGS:
        raise ValueError("probe cell is not configured for live simulation")
    if settings.get("neutralization") not in ALLOWED_NEUT_BY_REGION.get(region, ()):
        raise ValueError("probe neutralization is not valid in this region")
    max_trade, max_position = settings.get("maxTrade", "OFF"), settings.get("maxPosition", "OFF")
    if max_trade not in ("ON", "OFF") or max_position not in ("ON", "OFF"):
        raise ValueError("probe maxTrade/maxPosition must be ON or OFF")
    if max_position == "ON" and region in NO_MAX_POSITION_REGIONS:
        raise ValueError(f"probe maxPosition is not available for region {region}")
    if MAX_TRADE_POSITION_CONFLICT and max_trade == max_position == "ON":
        raise ValueError("probe maxTrade and maxPosition cannot both be ON")
    language = settings.get("language")
    if language not in ("FASTEXPR", "PYTHON") or settings.get("instrumentType") != "EQUITY":
        raise ValueError("probes require FASTEXPR or PYTHON equity settings")
    if language == "FASTEXPR" and settings.get("unitHandling") != "VERIFY":
        raise ValueError("probes must verify platform units")
    if language == "PYTHON" and ("unitHandling" in settings or "nanHandling" in settings):
        raise ValueError("Python probes must omit unsupported unitHandling and nanHandling settings")
    # Numeric bounds verified against live OPTIONS /simulations, 2026-10-16.
    decay, truncation = settings.get("decay"), settings.get("truncation")
    if type(decay) is not int or not 0 <= decay <= 512:
        raise ValueError("invalid probe decay")
    if isinstance(truncation, bool) or not isinstance(truncation, (int, float)) or not math.isfinite(truncation):
        raise ValueError("invalid probe truncation")
    if not 0 <= truncation <= 1:
        raise ValueError("invalid probe truncation")
    matrix, vectors, groups = target_pools(conn, region, universe, delay)
    if language == "PYTHON":
        if len(expressions) != 1:
            raise ValueError("Python pilot probes require one source per owner")
        if type(settings.get("lookback")) is not int or not 0 <= settings["lookback"] <= 1024:
            raise ValueError("Python probes require lookback between 0 and 1024")
        validate_python_source(expressions[0], matrix - groups - GROUP_NAMES)
        return
    operators = load_operator_names(conn)
    for expression in expressions:
        problem = parse_error(expression, operators)
        if problem:
            raise ValueError(problem)
        count = operator_count(expression)
        if count > 64:
            raise ValueError(f"probe expression has {count} operators; platform limit is 64")
        expanded = validation_expressions(expression, matrix | vectors | groups | operators)
        for value in expanded:
            problem = filled_expression_problem(value, matrix, operators, vectors, groups)
            if problem:
                raise ValueError(problem)
        if not (_value_tokens(expanded[-1]) & (matrix | vectors)) - groups - GROUP_NAMES:
            raise ValueError("probe must reference at least one scoped data field")
