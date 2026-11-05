# Development and validation

## Work boundaries

The BRAIN goal was explicitly resumed on October 23, 2026 (Asia/Shanghai).
Development supporting that goal is authorized. Documentation-only validation
still must not open the live DB or restart the explorer.

Use the host `.venv/bin/python`, provisioned with `make setup-dev`. Development does not require starting the explorer. See [Setup](SETUP.md).

Keep unrelated working-tree changes. No commit, push or PR is implied by documentation or local debugging requests.

## Dependencies and parser

FASTEXPR probe validation also enforces the native 64-operation limit with
`generator/operator_count.py`. It counts each variable assignment once and
does not count signs on numeric literals as operations. The October26 native
audit matched5000stored counts; regressions include the rejected66-operation
India batch and its equivalent factored expressions. Python probes bypass this
FASTEXPR rule. Focused validation:48tests passed; Ruff checks passed. Evidence:
`brain_logs/operator_count_audit_20261026.json`.

Python metadata: >=3.12. Existing runtime: Python 3.12 with requests, DuckDB and py-fastplus. Runtime versions are pinned in `requirements.txt`, including DuckDB 1.5.6. Dev tools are in `requirements-dev.txt`.

`vendor/fastplus` holds the Rust/PyO3 parser source and grammar. Runtime normally uses a wheel. Rebuilding needs Cargo/rustc, maturin and a C linker; Rust CI also needs a usable Python/PyO3 link path.

## Makefile targets

Run in an authorized development context, not against a second live writer.

| Target | Actual effect |
|---|---|
| `make test` | pytest verbose |
| `make lint` | Ruff check |
| `make format-check` | Ruff format verification |
| `make format` | Rewrites formatting; not a read-only check |
| `make typecheck` | mypy on project modules |
| `make security` | Bandit |
| `make deadcode` | Vulture |
| `make complexity` | Radon |
| `make rust-ci` | Cargo tests for the vendored parser |
| `make ci` | format-check, lint, typecheck, security, deadcode, Python tests, Rust tests |
| `make all` | Includes mutating format plus the other quality gates |
| `make sweep` | Template rendering/type validation; needs a DB source |
| `make profile` | Opens the production DB; not safe alongside the explorer |

Override `PYTHON` explicitly when needed. No claim is made that every gate passes from a Python test result alone.

## Testing without competing DB access

Use synthetic/in-memory fixtures for behavior changes. Never allow tests to read or write the live production file merely because its lock happens to be free.

The dated harness `brain_logs/run_quarter_goal_tests_20261021.py` ran the full suite with:
- temporary log, budget and expression-ledger paths;
- guards rejecting production DB opens through both the compatibility connection and raw DuckDB;
- the same project Python used by the runner.

That harness is gitignored campaign tooling, not a general portable test command. Review its paths before reuse. The ordinary test suite also has production-data tests whose skips are not proof of DB contents.

Latest executed code-change validation: **1,440 passed,16 skipped in 68.22s**, five focused role tests, Ruff check and diff checks. Log: `brain_logs/city_code_guard_full_pytest_20261021.log`. It covers the city-code role change and earlier work; documentation was subsequently checked separately without rerunning the service.

## Changing production behavior

Read existing tests and active constraints; make a targeted change; test the relevant behavior; then perform required broader checks. For runtime changes, record pending native handles before a controlled restart and verify their recovery. Do not restart due to observation timeouts. Never classify current opaque native failures using a local parser PASS alone.

## Documentation contribution checklist

- Keep current instructions concise and route detailed topics through `docs/README.md`.
- Keep dated outcomes in the handoff/artifacts, not daily appendices in every guide.
- Check linked local paths, source module names, CLI options, Makefile behavior and runtime layout.
- Label examples with DB/network/mutation effects.
- Never publish credentials, personal cookie/unsubscribe tokens or raw account secrets.
- Archive historical investigations with an explicit historical banner/index.
- Docs-only verification must leave the goal state, automations, service state, live DB and WAL untouched.
