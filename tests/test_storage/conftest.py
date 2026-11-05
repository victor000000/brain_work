"""Shared fixtures + alpha-data factory for storage tests."""

from core.db import connect, init_tables


def conn():
    """Fresh in-memory DB with the simulation schema applied."""
    c = connect(":memory:")
    init_tables(c)
    return c


def settings():
    """Minimal settings dict accepted by store_alpha + store_sim."""
    return {"neutralization": "INDUSTRY", "decay": 4, "truncation": 0.08}


def alpha_data(alpha_id="test123"):
    """Build an alpha-shaped dict matching what BRAIN's alpha-detail endpoint returns."""
    return {
        "id": alpha_id,
        "is": {
            "sharpe": 1.5,
            "fitness": 0.8,
            "turnover": 0.3,
            "returns": 0.01,
            "drawdown": -0.05,
            "margin": 0.02,
            "pnl": 100,
            "longCount": 50,
            "shortCount": 50,
            "riskNeutralized": {"sharpe": 1.2, "fitness": 0.7},
        },
        "train": {"sharpe": 1.4, "fitness": 0.75},
        "test": {"sharpe": 1.1, "fitness": 0.6},
        "regular": {"operatorCount": 5},
        "grade": "A",
        "status": "COMPLETE",
        "dateCreated": "2026-04-09",
    }
