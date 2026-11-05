.PHONY: setup setup-dev install-service progress lint format format-check test cov typecheck security deadcode complexity check ci all health profile sweep start stop status blacklist-update fastplus rust-ci

# Keep runtime and quality checks on the same host Python 3.12 environment.
PYTHON ?= $(CURDIR)/.venv/bin/python

setup:
	uv venv --allow-existing --python 3.12 .venv
	uv pip install --python .venv/bin/python -r requirements.txt

setup-dev: setup
	uv pip install --python .venv/bin/python -r requirements-dev.txt

install-service:
	@mkdir -p "$$HOME/.config/systemd/user"
	sed 's|@PROJECT_DIR@|$(CURDIR)|g' tools/brain-work-explorer.service > "$$HOME/.config/systemd/user/brain-work-explorer.service"
	systemctl --user daemon-reload

# ── Quality checks ────────────────────────────────────
lint:
	$(PYTHON) -m ruff check .

format:
	$(PYTHON) -m ruff format .

format-check:
	$(PYTHON) -m ruff format --check .

test:
	BRAIN_TEST_OFFLINE=1 $(PYTHON) -m pytest --disable-socket -v

cov:
	BRAIN_TEST_OFFLINE=1 $(PYTHON) -m pytest --disable-socket --cov=. --cov-report=term-missing -q

typecheck:
	$(PYTHON) -m mypy --ignore-missing-imports core/ generator/ runner/ storage/ checker/ download/ *.py

security:
	$(PYTHON) -m bandit -r core/ generator/ runner/ storage/ checker/ download/ tools/ *.py -c pyproject.toml -q

deadcode:
	$(PYTHON) -m vulture core/ generator/ runner/ storage/ checker/ download/ *.py --min-confidence 80

complexity:
	$(PYTHON) -m radon cc core/ generator/ runner/ storage/ checker/ download/ *.py -s -n C

health:
	$(PYTHON) -m tools.healthcheck

# Render every registered template in every configured cell and validate each
# render (syntax, operator allowlist, field membership, field types). This is
# the check that caught `hump(x, 0.05)` failing every render and the
# `target_tvr` keyword being read as a field, both before they could cost a
# simulation — run it after touching the registry, the pickers or the
# skeleton-fill path. When the explorer locks the live database, the default
# announces and reads the newest readable timestamped snapshot.
sweep:
	$(PYTHON) tools/registry_sweep.py

profile:
	$(PYTHON) -c "import cProfile,pstats;from core.db import get_conn;from generator.random_generator import generate_expressions;\
	conn=get_conn();prof=cProfile.Profile();prof.enable();[generate_expressions(conn,'USA',1,'TOP3000',10) for _ in range(5)];\
	prof.disable();pstats.Stats(prof).sort_stats('cumulative').print_stats(10)"

# The host interpreter supplies the native Python library path for PyO3.
# Environment RUSTFLAGS still takes precedence.
PYTHON_LIBDIR ?= $(shell $(PYTHON) -m tools.python_library)
RUSTFLAGS ?= -L $(PYTHON_LIBDIR)

check: lint test security  ## Run all quality checks

ci: format-check lint typecheck security deadcode test rust-ci  ## CI gate — must be green before merging

all: format lint test security deadcode typecheck complexity rust-ci  ## Full quality suite

# ── Simulation management ─────────────────────────────
# `start` goes through the supervisor (tools/run_explorer_supervised.sh), which
# respawns the explorer if it is killed outright — the entry point can only
# restart itself for exceptions it actually catches, and on 2026-10-05 the
# process died twice with no trace and stayed down. `stop` must therefore kill
# the supervisor too, or it would immediately restart what was just stopped.
#
# TEMPLATE_MIX is the share of candidates that try the mined forum/cnhkmcp
# corpora before the built-ins (generator/template_source.py). At 1.0 every
# candidate tries the pool first and falls back to a built-in template only
# when the pool cannot fill one — the corpus is the primary source, and the
# curated templates remain the safety net.
#
# Measured on 2026-10-05: the mined pool reaches the submission sharpe floor at
# 0.26% of its alphas against 2.46% for the built-ins, and at 1.0 that cost
# dominated — 90 consecutive generated alphas produced nothing at the floor
# against 6.5% for the 1,343 alphas before the change. 0.3 keeps a standing
# share of community shapes in every batch without letting them crowd out the
# templates that clear checks. Set TEMPLATE_MIX=1.0 to try the pool first
# everywhere.
#
# Re-measured 2026-10-07 and cut to 0.1. The gap had widened rather than
# closed: `pool:forum` was 1,155 of the day's 4,393 alphas (26%, the mix
# working as configured) and produced **2** at the floor, 0.2%, against 175 of
# 3,238 (5.4%) for the built-ins. The built-in side also improved under it —
# `get_weight` had made 21 of the 38 registry templates unselectable, and
# fixing that brought the starved shapes back. 0.1 keeps a standing share, so
# the corpus is still exercised and its shapes still reach the mix, while
# cutting what that share costs by roughly threefold. Not 0: correlation is the
# binding submission gate, and the mined corpus is the only source of
# community-shaped signals to be uncorrelated with.
TEMPLATE_MIX ?= 0.1

start:
	@systemctl --user set-environment BRAIN_TEMPLATE_MIX=$(TEMPLATE_MIX)
	systemctl --user start brain-work-explorer.service

stop:
	systemctl --user stop brain-work-explorer.service

status:
	@systemctl --user status brain-work-explorer.service --no-pager || true
	@tail -1 brain_logs/budget.log 2>/dev/null || true

# Progress for one day (default: today, UTC) from the logs. Unlike `status`
# this needs no DB lock, so it works while the explorer is running.
progress:
	@$(PYTHON) -m tools.progress_from_log $(DAY)

# ── Maintenance ───────────────────────────────────────
blacklist-update:
	$(PYTHON) -m download.blacklist_group_unit

# ── Vendored native dependency ────────────────────────
# fastplus is a Rust/PyO3 crate; vendor/fastplus holds its source and
# src/fastplus.pest, the authoritative Fast Expression grammar. Building needs
# a Rust toolchain (rustc + cargo), maturin, and a C linker (build-essential) —
# rustc links its own output through `cc`, so a C compiler is required even
# though no C is compiled directly.
#
# CI compiles the vendored crate and runs its own tests: the syntax checker the
# generator validates every expression with is half Rust (generator/validate.py
# calls fastplus), and a Python-only gate would not notice a broken grammar or
# parser build.
# PYO3_PYTHON: pyo3's build script searches PATH for an interpreter, and this
# box has no `python3` on PATH (everything lives in the venv) — without the
# explicit path the build dies with "no Python 3.x interpreter found". maturin
# sets this itself in the `fastplus` target; a plain cargo invocation must not.
rust-ci:
	@command -v cargo >/dev/null 2>&1 || { echo "cargo not found — install from https://rustup.rs (the vendored fastplus crate needs it)"; exit 1; }
	cd vendor/fastplus && PATH="$$HOME/.cargo/bin:$$PATH" PYO3_PYTHON="$(abspath $(PYTHON))" RUSTFLAGS="$(RUSTFLAGS)" LD_LIBRARY_PATH="$(PYTHON_LIBDIR):$${LD_LIBRARY_PATH:-}" cargo test --locked --quiet

fastplus:
	@command -v cargo >/dev/null 2>&1 || { echo "cargo not found — install from https://rustup.rs"; exit 1; }
	@command -v cc >/dev/null 2>&1 || { echo "no C linker — apt-get install build-essential"; exit 1; }
	cd vendor/fastplus && \
		PATH="$$HOME/.cargo/bin:$$PATH" \
		RUSTFLAGS="$(RUSTFLAGS)" \
		VIRTUAL_ENV="$$(dirname $$(dirname $(PYTHON)))" \
		$(PYTHON) -m maturin build --release -o /tmp/fpwheel
	uv pip install --python "$(PYTHON)" --force-reinstall /tmp/fpwheel/*.whl
