# Setup

## Offline development

Requirements: native Linux/WSL, Python 3.12, Bash, make and access to package repositories. Use a fresh environment in a new checkout:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install --require-hashes -r requirements-ci.txt
.venv/bin/python -m pip check
make docs-check
make test
```

Alternatively, `make setup-dev` uses uv to create/reuse `.venv` and install runtime/development requirements. Do not reprovision a live service environment for documentation validation. Python metadata permits >=3.12; the hosted CI validates 3.12, not every newer version. `requirements.txt` pins requests 2.34.2, py-fastplus 0.3.5 and DuckDB 1.5.6. Keep writer version compatibility in mind when upgrading existing data.

`make ci` also builds/tests the vendored Rust parser: install a stable Rust toolchain and a C linker. Cargo may download dependencies. No live credentials or DB are needed. See [Development](DEVELOPMENT.md).

## Runtime provisioning (separate authorization)

Runtime uses the same project Python and embedded DuckDB; no database server or Docker image is required. For runtime-only dependencies use `make setup`. Restore private credentials using [Configuration](CONFIGURATION.md); source checkout does not restore datasets, receipts, budget state or account entitlement.

The optional user service needs systemd, `flock` from util-linux and a persistent Linux/WSL host. Inspect `tools/brain-work-explorer.service` and `tools/run_explorer_supervised.sh` first. `make install-service` renders this checkout's absolute path into the user unit and reloads the manager; it does not start or enable research. Installation is a host change and was not executed to verify these docs.

`make start` starts the supervisor and may submit simulations/alphas. `make stop` stops its whole control group. `make status` and `make progress` inspect service/logs without opening DuckDB. Use [Operations](OPERATIONS.md) and the deployment owner's latest authorization before lifecycle actions.

Enabling the user unit or enabling user lingering is a separate decision about unattended research. WSL must remain running. Re-render the unit if the checkout moves; never point a second deployment at the same live DB. Do not reuse a venv with interpreter paths from another machine/container.
