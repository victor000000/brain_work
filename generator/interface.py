"""Alpha Generator Interface — single swap point.

The platform imports ONLY from this file.
Any generator must provide:
    generate(conn, region, delay, universe, count, neutralization=None) -> list[str]

Current:  random_alpha_generator  (random with weighted diversity)
Future:   ai_alpha_generator      (LLM-guided)
Future:   hybrid_alpha_generator  (AI + random)
"""

# --- SWAP GENERATOR HERE ---
from generator.random_generator import generate_expressions as generate  # noqa: F401
