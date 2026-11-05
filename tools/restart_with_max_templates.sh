#!/bin/bash
# Restart the explorer with maximum template diversity.
#
# This used to `pkill` and then `nohup simulate_alphas.py` directly, which
# bypasses the supervisor — and a bare nohup start is exactly what left the
# process down overnight on 2026-10-05 (see the Makefile's `start` comment).
# The mix is a Makefile knob now, so this is a two-line wrapper over it.
set -euo pipefail
cd "$(dirname "$0")/.."

make stop
make start TEMPLATE_MIX=0.75

echo "Restarted with TEMPLATE_MIX=0.75 (75% mined templates, 25% built-ins)"
echo "  monitoring: tail -f brain_logs/explore.log"
