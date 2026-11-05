# brain_work

WorldQuant BRAIN research engine: generate Fast Expression alphas, simulate them, collect results, evaluate native checks, and verify submissions. Research state lives in DuckDB; portable analytical exports use Parquet.

**Runtime: native Linux/WSL with Python 3.12 in `.venv`. Docker is not used.** Research was resumed on October 23, 2026; see [the handoff](docs/CURRENT_STATE.md) for campaign state and ownership constraints.

## Start here

| Need | Read |
|---|---|
| Host environment, dependencies and service setup | [Setup](docs/SETUP.md) |
| Start/stop, job ownership, budget and recovery | [Operations](docs/OPERATIONS.md) |
| Module responsibilities and execution flow | [Architecture](ARCHITECTURE.md) |
| Environment variables, credentials and defaults | [Configuration](docs/CONFIGURATION.md) |
| DuckDB tables, WAL, Parquet and exports | [Data and storage](docs/DATA.md) |
| Ideas, templates, experiments and Expert metrics | [Research workflow](docs/RESEARCH.md) |
| Tests, lint and contribution checks | [Development](docs/DEVELOPMENT.md) |
| Problems with setup, HTTP, jobs or results | [Troubleshooting](docs/TROUBLESHOOTING.md) |
| Daily Gmail Inbox + Spam research archive | [Email research](docs/EMAIL_RESEARCH.md) |
| Tool entry points and side effects | [Tools guide](tools/README.md) |
| All documentation and reference material | [Documentation index](docs/README.md) |

## Scope

- **Simulation inputs:** PV/options value fields only, with legitimate GROUP fields used as partitions. Field category and MATRIX type alone do not establish numeric meaning.
- **Research archive:** ideas from every dataset category, including fundamental, model, news and sentiment. Saving an idea does not authorize simulating it.
- **External data provider:** US and mainland China raw PV/options data and calculated historical values; HK is excluded from that provider request. This is separate from the BRAIN simulation region matrix. [Current provider requirements](docs/data_requirements/CURRENT_BRAIN_PV_OPTIONS_REQUIREMENTS.md).
- Native simulation acceptance, local check passes, verified alpha acceptance, and published combined OS performance are different milestones.

## Runtime on this machine

The project runs directly in `/home/vic/brain_work`, using `.venv/bin/python` and the user service `brain-work-explorer.service`. DuckDB, credentials, logs, quota state and request receipts stay in their existing locations.

```bash
make setup-dev       # Python 3.12 runtime and development tools; requires uv
make install-service # Register the user service; does not start it
make status          # Service state and quota log; no database connection
make progress        # Log-only progress
```

For an authorized campaign, `make start` launches the supervised explorer; `make stop` stops the service and all its children. Setup alone does not start research. See [Setup](docs/SETUP.md) for persistence across logout/reboot.

## Storage and request ownership

The explorer is the sole process allowed to open the live DuckDB while it runs. Other processes must use logs, existing exported artifacts, or native GET observers that do not fall back to the DB. Keep the live DB, its WAL when present, and Parquet. Do not create routine DB backups, add blacklists, reset quota state, or replay uncertain simulation/submission POSTs.

The latest pause checkpoint is `brain_logs/user_pause_checkpoint_20261021.json`. It preserves six pending accepted parents and historical uncertain owners. Detailed resume conditions are in [Operations](docs/OPERATIONS.md).

## Development

Python metadata requires 3.12 or newer; setup selects Python 3.12 for parser-wheel compatibility. Runtime dependencies are pinned in `requirements.txt`, including DuckDB 1.5.6 to match the existing database writer.

The last completed isolated suite was **1,440 passed, 16 skipped**, before the documentation-only reorganization. Full CI has additional gates; that test result is not a claim that every CI target was run. [Validation instructions](docs/DEVELOPMENT.md).

## Documentation policy

Current operating rules live in the guides above and the compact [agent instructions](CLAUDE.md). [TODO](TODO.md) holds current unresolved work. Long investigations are retained under [docs/archive](docs/archive/README.md); archived commands, budgets and account observations are historical, not instructions to execute.
