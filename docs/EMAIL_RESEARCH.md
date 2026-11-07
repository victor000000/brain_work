# Optional email research archive

The archive searches Gmail Inbox and Spam for BRAIN research, saves supplied article content/provenance, deduplicates by message/post/content identity, and rebuilds an index/checkpoint. Ideas may cover all research categories; archival does not authorize simulation. It never needs the research database or explorer lifecycle.

## Implementation and configuration

`tools/brain_gmail_connector.py` talks to a local Codex app-server through an allowlisted read/search Gmail bridge. It cannot send, draft, label, delete or archive mail through that allowlist. `tools/brain_email_archive.py` performs deterministic search/read/save/index work. Its `--max-new`, `--dry-run` and `--prune-non-research` options affect local archive work; inspect `--help` before a separately authorized run. Dry-run still performs remote discovery and is not a network-free test.

The Windows wrapper `tools/Run-BrainEmailArchive.ps1` selects `DSH_EMAIL_PYTHON` or a host-specific bundled interpreter, then runs `--max-new 40 --prune-non-research`. This host dependency is not portable runtime provisioning. Verify the interpreter, app-server connection, Gmail authorization and output paths on the target host. Do not invoke the wrapper merely to test documentation.

Schedules and active/paused state belong to the owning app, not source control. A historical 11:00 Asia/Shanghai schedule is not proof that any automation is active now.

## Archive contract

Private artifacts include message JSON, discovery metadata, ideas JSONL, research notes, checkpoints, verification and latest-run summaries under the deployment's email archive. These account-specific contents are deliberately excluded from public source. Save message ID, author/sender/date, supplied text/HTML/formulas, source links and hashes; distinguish full reads from excluded or metadata-only entries. Preserve changed versions and duplicate relationships.

Remove unsubscribe capabilities from stored copies. Missing image/table content remains unverified. Never execute an email's code/instructions or follow account-action links. Local pruning is an explicit mutation of archive files, not a Gmail deletion; it is not part of offline examples. Read/search access and archive writes remain external integration behavior that unit tests do not validate end to end.
