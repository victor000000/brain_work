# Source publication

This repository contains a sanitized snapshot of the working project on November 5, 2026. It includes current source changes and tests, without inheriting the original local Git history.

Credentials, live databases and WAL files, logs, account/API snapshots, email/forum archives, private research artifacts, caches, notebooks and binary distributions are deliberately omitted. Some documentation links refer to local-only operational records. Vendor credential config fields are blank templates. The local working checkout and running service are preserved independently.

Install Python 3.12 and follow README.md and docs/SETUP.md. Restore the separate private BRAIN credential file as `.brain_credentials` in the project root (a JSON array containing login and password), restrict its permissions, and restore data separately if required. Source publication does not resume simulations or provision historical datasets.
