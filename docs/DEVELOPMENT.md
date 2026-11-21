# Development and validation

## Reproduce CI

Install the pinned validation dependencies in a clean Git checkout of the publication source. Ruff uses the checkout’s ignore rules to skip the in-tree virtual environment. For an unpacked archive, keep the environment outside the source directory and pass its interpreter using the Makefile’s `PYTHON` override. Use a shell without deployment overrides for log, budget or ledger paths. For the native parser, make sure `cargo`, `rustc` and `cc` are on `PATH`. Check which Python shared-library directory the build will use.

```bash
.venv/bin/python -m tools.python_library
```

Run the same gates as GitHub Actions from the repository root. Set the report path to keep the unit results locally.

```bash
results_dir=$(mktemp -d)
PYTEST_ADDOPTS="--junitxml=$results_dir/results.xml" CARGO_BUILD_JOBS=2 make ci
```

`make ci` runs docs-check, format-check, lint, typecheck, security, deadcode, test and rust-ci. The last target builds the vendored fastplus crate and runs `cargo test --locked`. With all crates cached, set `CARGO_NET_OFFLINE=true` for a disconnected run. Installation prerequisites are in [Setup](SETUP.md).

The **Offline validation** workflow runs on pushes, pull requests and manual dispatches. It installs the lock with pip on Ubuntu 24.04 and CPython 3.12, uses stable Rust, and gives the checkout read-only repository permissions. Pytest writes `test-results.xml` inside the job workspace. The retained Actions log contains the test summary. [Workflow](../.github/workflows/ci.yml)

## Focused checks

```bash
make docs-check
BRAIN_TEST_OFFLINE=1 .venv/bin/python -m pytest --disable-socket -q \
  tests/test_docs_links.py tests/test_budget_persistence.py \
  tests/test_runner_fixes/test_flow_guard.py tests/test_submission_request_reconciliation.py
```

`make test` and `make cov` set both offline controls. Pytest disables sockets, the test harness rejects a raw DuckDB connection to the checkout's project database, and corpus-dependent tests skip. Temporary synthetic databases are available. Budget and expression-ledger defaults are isolated by the test fixtures. The link checker verifies owned Markdown inline local links and heading fragments. External URLs and vendored manuals fall outside its scope. [Test fixtures](../tests/conftest.py) · [Link checker](../scripts/check_docs.py)

| Target | Effect |
|---|---|
| `make format-check`, `make lint` | Verify formatting and lint with Ruff |
| `make typecheck`, `make security`, `make deadcode` | Run mypy, first-party Bandit and Vulture |
| `make test`, `make cov` | Full offline Python tests, optionally with coverage |
| `make rust-ci` | Build the locked native parser and run its tests |
| `make format`, `make all` | Can rewrite source formatting |

## Dependency and parser changes

Runtime pins are in `requirements.txt`. When deliberately changing dependencies, regenerate the CI lock from the runtime and development inputs, then install it in a fresh environment and run CI.

```bash
uv pip compile --python .venv/bin/python requirements.txt requirements-dev.txt --generate-hashes -o requirements-ci.txt
```

Runtime uses the py-fastplus wheel. For an optimized build of the vendored Rust library, run the following after setting up the validation environment.

```bash
parser_libdir=$(.venv/bin/python -m tools.python_library)
PYO3_PYTHON="$PWD/.venv/bin/python" RUSTFLAGS="-L $parser_libdir" CARGO_BUILD_JOBS=2 \
  cargo build --locked --release --manifest-path vendor/fastplus/Cargo.toml
```

Rebuilding and reinstalling a **Python wheel** with `make fastplus` also needs uv on `PATH` and Maturin installed in the selected Python environment. That target builds into `/tmp/fpwheel` and reinstalls matching wheels, so use a dedicated build environment. The supported Maturin range is in the [parser build metadata](../vendor/fastplus/pyproject.toml). FASTEXPR operator counting and Python probe validation have separate tests.

Use synthetic headers and a controlled clock for quota and reset tests. Keep generated fixture timestamps inside the miner's rolling lookback window. For a release, the owner verifies the published source tree and the workflow result for its exact commit. [Release procedure](../PUBLICATION.md)
