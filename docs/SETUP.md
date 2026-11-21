# Setup

## Install validation dependencies

Work from the repository root in a clean Linux or WSL checkout. The GitHub workflow uses CPython 3.12 on Ubuntu 24.04. The Python checks require GNU Make. Full CI also needs a stable Rust toolchain with Cargo, a C linker available as `cc`, and the active Python interpreter's shared library.

The [README quick start](../README.md#start-here) installs the hash-pinned validation environment with uv. On a host with Python 3.12 and its `venv` and `ensurepip` modules installed, use the equivalent pip commands below.

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install --require-hashes -r requirements-ci.txt
.venv/bin/python -m pip check
make docs-check
make test
```

If Python 3.12 is installed outside `PATH`, use the full path to that interpreter for the first command. A uv-created environment can omit pip. Use `uv pip check --python .venv/bin/python` in that environment. The Makefile uses `.venv/bin/python` directly, so activation is optional.

### Cached installation

With CPython 3.12 already installed and all packages from the lock in the local uv cache, this sequence keeps installation and validation offline.

```bash
UV_OFFLINE=1 UV_PYTHON_DOWNLOADS=never uv venv --python 3.12 .venv
UV_OFFLINE=1 uv pip install --python .venv/bin/python --require-hashes -r requirements-ci.txt
uv pip check --python .venv/bin/python
make docs-check
make test
```

Provision any missing locked distributions before going offline. For offline Rust tests, the crates in the vendored parser's `Cargo.lock` must also be cached. See [Development](DEVELOPMENT.md#reproduce-ci).

## Runtime environment

`make setup` uses uv to create or reuse the project environment and install the runtime pins. `make setup-dev` also installs the development requirements. The release checks use the complete, hash-pinned [CI lock](../requirements-ci.txt). The runtime DuckDB pin matters when opening an existing DB and WAL. [Configuration](CONFIGURATION.md) covers private credential lookup and [Data](DATA.md) describes storage.

## Optional user service

The runtime service needs Bash, `flock` from util-linux and a running systemd user manager. On WSL this applies to the Linux distribution hosting the writer. Run lifecycle commands from the intended deployment checkout under the account that owns that manager. One supervisor and its maintenance tools must use the same log directory for `explorer.lock`.

Preview the installation from the deployment checkout.

```bash
make -n install-service
```

`make install-service` writes the rendered unit under `~/.config/systemd/user/` and reloads the user manager. The unit records the checkout's absolute working directory and Python path. Render it again if the deployment moves. Starting the unit, enabling it for later login and configuring user lingering are separate operations. Start only in an authorized research window after reconciling pending work. [Service template](../tools/brain-work-explorer.service) · [Startup and recovery](OPERATIONS.md)
