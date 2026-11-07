# brain_work

Version 1.0.1 is a Python research engine for WorldQuant BRAIN: generate expressions, simulate, collect native results, inspect checks and verify submission outcomes. It stores research state in DuckDB and exports metadata/analysis as Parquet. Source tests do not establish profitability or Expert promotion.

## Start here

Use native Linux/WSL and Python 3.12. No Docker runtime is required. In a fresh checkout, safe offline validation is:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install --require-hashes -r requirements-ci.txt
.venv/bin/python -m pip check
make docs-check
make test
```

Installation downloads packages; tests disable sockets and deny production-DB access. Full `make ci` additionally requires Rust and a C linker. No credentials, running service or market dataset is needed for offline tests. See [Setup](docs/SETUP.md) for runtime provisioning and [Development](docs/DEVELOPMENT.md) for the complete CI contract.

| Task | Guide |
|---|---|
| Understand modules and evidence stages | [Architecture](ARCHITECTURE.md) |
| Configure credentials, paths and controls | [Configuration](docs/CONFIGURATION.md) |
| Manage a separately authorized research run | [Operations](docs/OPERATIONS.md) |
| Understand data, receipts and exports | [Data](docs/DATA.md) |
| Design PV/options experiments | [Research](docs/RESEARCH.md) |
| Diagnose a failure | [Troubleshooting](docs/TROUBLESHOOTING.md) |
| Choose a CLI by its side effects | [Tools](tools/README.md) |
| Browse all guides and historical references | [Documentation index](docs/README.md) |

## Scope and boundaries

PV/options measurement inputs are the research scope; category labels and name prefixes alone do not establish economic meaning. Legitimate grouping metadata is for partitioning. The latest retained project design adds an atom-only policy (one numeric measurement field), but the published runtime does not yet enforce that policy structurally across every path. [Research](docs/RESEARCH.md) distinguishes policy, implemented checks and remaining gaps.

One process owns the live database. Setup and service installation do not authorize simulations or submissions. Starting the explorer can generate native POSTs and launch background submission checks. Preserve uncertain request owners; observation timeouts never authorize replay.

Live service state, account status, automations, receipt ledgers, credentials and historical datasets are not included in this publication. Consult the deployment owner's private handoff before runtime operations; no README can certify the current host state. [Publication contract](PUBLICATION.md).

Provider acquisition/storage belongs to the separate data-provider project. Screener risk/execution UI and broker orders belong to their own projects. This repository's backtests and native BRAIN acceptance do not establish data-provider delivery, broker execution or portfolio performance.
