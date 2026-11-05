# Native Linux / WSL setup

Docker is not required. The application uses Python, requests, the py-fastplus parser wheel and embedded DuckDB; it needs no separate database server.

## Environment

Install `uv`, `make`, Bash and `flock` (util-linux), then run in the project:

```bash
make setup-dev
.venv/bin/python --version
make install-service
```

Setup creates `.venv` using Python 3.12 and installs `requirements.txt`. `make setup` installs runtime dependencies only. Python 3.12 is selected for parser wheel compatibility; the system Python may be newer. Cargo, Rust, maturin and a C linker are needed only to rebuild the vendored parser or run Rust CI. Do not reuse `~/.venvs/brain_work`: it contains old `/root` paths.

Runtime requirements match the former container: requests 2.34.2, py-fastplus 0.3.5 and DuckDB 1.5.6. Keep the DuckDB writer version pinned. Credentials remain in `.brain_credentials`; never copy them into the service. Run as the workspace owner, not root. Database, WAL, logs, budget state and request ledgers remain in place; migration does not copy or reset them.

## Service lifecycle

The installer registers `brain-work-explorer.service` under `~/.config/systemd/user/`, with this checkout's absolute path. Reinstall if the checkout moves. Installing does not start or enable it.

```bash
make start     # Only when research is authorized
make status    # Service and log inspection; no DB connection
make progress  # Log-only reporting
make stop      # Stops supervisor and all children
```

The supervisor restarts failed explorers with backoff. The service owns the process group so a stop cannot leave its explorer running. A workspace lock rejects a second supervisor. The legacy BRAIN container and image have been removed; do not recreate a container runner against the same database.

To start with the user manager after boot, explicitly enable the service:

```bash
systemctl --user enable brain-work-explorer.service
```

For continuous operation after logout, the host also needs user lingering (`loginctl enable-linger vic` on this installation). WSL itself must remain running; shutting down WSL stops host services. Check `loginctl show-user vic -p Linger`. Enabling persistent research must remain within campaign authorization.

For shell-only maintenance use `.venv/bin/python`. Only one process may open the live DuckDB; stop the service before database maintenance. Follow [Operations](OPERATIONS.md) for pending receipts and long-pause recovery.
