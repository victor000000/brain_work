# brain_work

brain_work generates expressions for WorldQuant BRAIN, runs simulations, stores results in DuckDB and verifies alpha submissions. It exports metadata and analysis as Parquet. The package version and supported Python versions are in the [project metadata](pyproject.toml).

## Start here

Use a fresh Linux or WSL checkout, GNU Make and CPython 3.12. With uv installed, run these commands from the repository root.

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python --require-hashes -r requirements-ci.txt
uv pip check --python .venv/bin/python
make docs-check
make test
```

The first installation needs package access or a populated cache. The unit suite runs with sockets disabled and uses synthetic state. A full CI run also builds and tests the vendored Rust parser. See [Setup](docs/SETUP.md) for the pip and offline installation options and [Development](docs/DEVELOPMENT.md) for the complete CI command.

| Task | Guide |
|---|---|
| Understand modules and evidence stages | [Architecture](ARCHITECTURE.md) |
| Configure credentials, paths and controls | [Configuration](docs/CONFIGURATION.md) |
| Inspect, pause or recover an authorized run | [Operations](docs/OPERATIONS.md) |
| Understand data, receipts and exports | [Data](docs/DATA.md) |
| Design PV/options experiments | [Research](docs/RESEARCH.md) |
| Diagnose a failure | [Troubleshooting](docs/TROUBLESHOOTING.md) |
| Choose a CLI by its side effects | [Tools](tools/README.md) |
| Verify and publish a source release | [Publication](PUBLICATION.md) |
| Browse the guides and historical references | [Documentation index](docs/README.md) |

## Research and deployment

Price/volume and options measurements are the numeric research inputs. Grouping fields serve as partitions. The atom-only design calls for one numeric measurement field. The published checks cover part of that policy. See [research scope and implementation limits](docs/RESEARCH.md).

One supervised explorer owns the live database. Starting it can submit simulations and launch background alpha checks. Obtain the active window and pending request ownership from the deployment owner's private handoff before starting or resuming it. Keep credentials, databases, logs and native receipts in that deployment. [Operating procedures](docs/OPERATIONS.md)

Provider acquisition and storage belong to the data-provider project. Screener risk controls and broker execution belong to their respective projects. Native acceptance, Expert promotion and portfolio performance each require their own evidence.
