# Remove legacy database credentials

Authentication uses private files or environment variables. Normal startup does
not query a credentials table, and the application does not create or write one.
Existing legacy values must be migrated separately before their removal can be
reported complete.

## Exclusive access and export

Prepare a maintenance window through the existing campaign owner. Preserve all
pending simulation/submission owners, and stop the supervised explorer only when
that lifecycle action is authorized. The migration itself never stops a service.
There is no arbitrary SQL/export command in the simulation probe inbox.

The migration takes the same `brain_logs/explorer.lock` flock as the supervisor.
If the writer still owns it, export and removal fail before opening DuckDB.
Do not bypass this guard, copy a live database, or create a second writer.

The examples require the owner to define the uppercase path/destination variables first; no account identifiers belong in committed scripts. Export opens the database read-only and may refuse a pending WAL that needs recovery. In that case keep exclusive ownership and preserve the WAL: the maintenance owner must arrange supported writer recovery/checkpointing under the same lock before retrying. The export CLI does not perform that lifecycle step or authorize deleting a WAL.

Use absolute paths and a new private output directory outside the repository:

```bash
.venv/bin/python -m tools.migrate_credentials export \
  --database "$PROJECT_DIR/brain_data.duckdb" \
  --lock-file "$PROJECT_DIR/brain_logs/explorer.lock" \
  --output-directory "$PRIVATE_EXPORT_DIR" \
  --drive-folder-id "$PRIVATE_DRIVE_FOLDER_ID" \
  --owner-email "$PRIVATE_DRIVE_OWNER"
```

`legacy_credentials.json` contains only the legacy credential key/value pairs,
with mode 0600 inside a mode-0700 directory. It is not a database backup.
`migration.json` is a local manifest, not a Drive upload. No business tables are
read or copied. The CLI prints counts and completion state, never secret values.
An unexpected schema or duplicate keys requires review rather than lossy export.

## Verify the private backup before removal

Using the connected Drive tools, verify the destination folder remains owner-only,
upload **only** `legacy_credentials.json`, then read the uploaded file's metadata.
Do not upload source code, database files, or the local manifest.

Save a private local receipt JSON with these fields:

```json
{
  "sha256": "the local manifest's exact export digest",
  "drive_metadata": {
    "id": "observed uploaded file ID",
    "size": "observed uploaded byte count",
    "parent_ids": ["the verified private folder ID"],
    "shared": false,
    "permissions": [
      {"type": "user", "role": "owner", "emailAddress": "the verified owner"}
    ]
  }
}
```

The receipt represents actual connector upload/readback, not an operator guess.
Its file mode must be 0600. Removal validates destination, sole owner, sharing,
size, export hash and current database values before dropping anything.

```bash
.venv/bin/python -m tools.migrate_credentials remove \
  --database "$PROJECT_DIR/brain_data.duckdb" \
  --lock-file "$PROJECT_DIR/brain_logs/explorer.lock" \
  --manifest "$PRIVATE_EXPORT_DIR/migration.json" \
  --backup-receipt "$PRIVATE_BACKUP_RECEIPT" \
  --credential-file "$PROJECT_DIR/.brain_credentials"
```

A complete legacy email/password pair creates the private login file if missing.
An existing valid login is preserved even when it selects a different account;
all old values remain in the private export/backup. An invalid existing login
must be repaired before removal. The transaction drops only `main.credentials`
and checkpoints afterward. Business tables remain intact. A checkpoint is not
forensic erasure of historical pages or external backups.

If the table is absent or empty, no credential file is uploaded and no Drive
receipt is required. Record that observed result; do not infer it from source.
Logical removal returns `migration_complete: false`: the physical phase is
required before claiming database credential removal is complete.

## Verify physical removal before restarting

Keep every database user stopped and run the third phase with the same private
manifest and verified backup receipt:

```bash
.venv/bin/python -m tools.migrate_credentials sanitize \
  --database "$PROJECT_DIR/brain_data.duckdb" \
  --lock-file "$PROJECT_DIR/brain_logs/explorer.lock" \
  --manifest "$PRIVATE_EXPORT_DIR/migration.json" \
  --backup-receipt "$PRIVATE_BACKUP_RECEIPT" \
  --credential-file "$PROJECT_DIR/.brain_credentials"
```

For a zero-row export, omit `--backup-receipt`. The physical phase combines
known values from the verified legacy export, current private login file and
complete login environment pair. It refuses a zero-value scan. Values and
matching bytes are never printed. Verification covers their exact UTF-8 bytes;
it does not claim forensic erasure of unallocated filesystem blocks or unknown
encoded variants.

If known bytes remain, use DuckDB's documented
[COPY FROM DATABASE rebuild](https://duckdb.org/docs/1.5/operations_manual/footprint_of_duckdb/reclaiming_space)
into a fresh, private same-filesystem candidate. This is an explicit stopped-DB
sanitization step, not a routine backup or a byte image of a live database.
Every business table is read for count and sorted SHA256 row-multiset verification.
Supported catalog definitions, columns, constraints, indexes, views, macros,
comments and checkpointed sequence next-state must match. Source sequences are
never advanced. Custom/complex types or other unsupported objects fail closed.

Allow at least `max(3 × database file size, 64 MiB)` free additional disk space
for the candidate and verification spill; available space is checked first.
Runtime includes full source/candidate scans and depends on database size and
storage. The original stays at its path until the candidate is reopened,
verified and scanned. Replacement is atomic, with a temporary private hardlink
to the dirty source for rollback; this hardlink does not duplicate the full file.
Successful cleanup unlinks it. After that unlink, rollback is only to the
verified clean database, not the discarded credential-bearing original.

An error preserves/restores the original where possible. Any reported
`rollback_path` or `cleanup_incomplete` means keep writers stopped and resolve
that artifact; it is not successful credential removal. Resume only after
`migration_complete: true`, `physical_removal_verified: true`, and no dirty
rollback path. Then validate file/environment loading without logging values,
let the campaign owner restore the prior service state, and reconcile pending
handles using GET only. Do not start additional research as a migration side effect.
