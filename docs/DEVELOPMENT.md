# Development and validation

## Reproduce CI

Use the [Setup](SETUP.md) fresh-checkout commands to install hash-pinned `requirements-ci.txt`. CI runs on Python 3.12 / Ubuntu 24.04 with a stable Rust toolchain, a C linker, immutable checkout/setup action references and read-only repository permissions. Installation/Cargo downloads require network; unit tests do not.

```bash
make docs-check
CARGO_BUILD_JOBS=2 make ci
```

`make test` sets `BRAIN_TEST_OFFLINE=1` and invokes pytest with `--disable-socket`. The harness rejects production-DB opens through the raw driver and skips corpus-only checks; temporary synthetic databases remain usable. Fixtures redirect logs, quota and expression-ledger paths. Run this target rather than an unguarded ad hoc whole-suite command. Never start an explorer, authenticate, download data or restart services to exercise a test.

| Target | Effect |
|---|---|
| `make docs-check` | Owned local Markdown links/anchors; no DB/network |
| `make test` | Full offline Python suite; corpus integrations skipped |
| `make cov` | Same isolation plus coverage report |
| `make format-check`, `make lint` | Ruff verification |
| `make format` | Rewrites formatting; inspect diff afterward |
| `make typecheck`, `make security`, `make deadcode` | mypy, first-party Bandit, Vulture |
| `make rust-ci` | Vendored fastplus tests; resolves host Python library via tools/python_library.py |
| `make ci` | Docs, format, lint, types, security, dead code, Python and Rust gates |
| `make all` | Includes mutating format and additional complexity reporting |

## Dependency and parser changes

`pyproject.toml` is version 1.0.1 and requires >=3.12; runtime pins live in `requirements.txt`. `make setup-dev` installs the development inputs with uv. After an intentional dependency update regenerate the CI lock with `uv pip compile requirements.txt requirements-dev.txt --generate-hashes -o requirements-ci.txt`, then validate it in a fresh venv and run CI. The lock is not generated during tests.

`vendor/fastplus` is the Rust/PyO3 parser source. Runtime normally uses the wheel. Local syntax/type checks cover only operators the parser knows and do not replace native verdicts. FASTEXPR operator counting and probe validation have dedicated tests; Python probes have a separate source-validation path.

## Review and publication

Use synthetic fixtures for ownership, incomplete checks, native payload errors and scope regressions. Preserve unrelated working-tree changes. Inspect the exact staged tree and commit only reviewed source/tests/docs; exclude credentials, DB/WAL, runtime logs and private research snapshots. See [Publication](../PUBLICATION.md).

GitHub runs the full workflow on push/PR/manual dispatch and emits JUnit output for unit tests. A local pass is not a hosted result: record the exact published SHA and terminal workflow result. API-created commits may have different SHAs from local candidates; compare full tree identities. There is no automatic deployment/CD stage. Runtime service activation and external account/corpus tests require their own authorization and evidence.

The November 7 release candidate passed 1624 Python tests with 16 corpus skips and 22 Rust tests before this documentation phase. Those dated results do not certify future commits. Current audit results belong in DOCS_AUDIT.md rather than an evergreen claim of complete production validation.
