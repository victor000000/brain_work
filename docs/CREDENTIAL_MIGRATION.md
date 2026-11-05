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
After removal, validate file/environment loading without logging the values,
then let the campaign owner resume the service and reconcile pending handles.
