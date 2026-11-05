"""Format one population's stats block for stdout."""

from tools._kpi_helpers import normalized_entropy


def _empty_block(label):
    return f"{label}:  N = 0\n  n/a (no alphas in this population)\n"


def format_block(label: str, stats: dict, p_max: int) -> str:
    """Format one population's report block."""
    n = stats["N"]
    if n == 0:
        return _empty_block(label)

    per_pyramid = stats["per_pyramid"]
    p = len(per_pyramid)
    s_p = p / p_max if p_max else 0.0
    s_h = normalized_entropy(per_pyramid)

    a_d = stats["A_dataset"]
    a_c = stats["A_category"]
    s_a_d = a_d / n
    s_a_c = a_c / n
    score_d = s_a_d * s_p * s_h
    score_c = s_a_c * s_p * s_h

    return (
        f"{label}:  N = {n}\n"
        f"  Pyramid coverage:    P = {p:>3} / {p_max}   (S_P = {s_p:.4f})\n"
        f"  Entropy:             normalized S_H = {s_h:.4f}\n"
        f"  Atom by dataset:     A = {a_d:>3}, S_A = {s_a_d:.4f}  ->  score = {score_d:.4f}\n"
        f"  Atom by category:    A = {a_c:>3}, S_A = {s_a_c:.4f}  ->  score = {score_c:.4f}\n"
    )
