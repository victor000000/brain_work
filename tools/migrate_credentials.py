"""Export legacy database credentials, then remove them after private backup.

This tool never stops the explorer. It requires its exclusive writer lock.
Credential values are written only to private files and never printed.
"""

import argparse
import json

from core.credential_migration import MigrationError, export_legacy, remove_legacy, sanitize_legacy


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    export = commands.add_parser("export")
    export.add_argument("--database", required=True)
    export.add_argument("--lock-file", required=True)
    export.add_argument("--output-directory", required=True)
    export.add_argument("--drive-folder-id", required=True)
    export.add_argument("--owner-email", required=True)
    for operation in ("remove", "sanitize"):
        action = commands.add_parser(operation)
        action.add_argument("--database", required=True)
        action.add_argument("--lock-file", required=True)
        action.add_argument("--manifest", required=True)
        action.add_argument("--backup-receipt")
        action.add_argument("--credential-file")
    args = parser.parse_args(argv)
    try:
        if args.command == "export":
            result = export_legacy(
                args.database, args.lock_file, args.output_directory, args.drive_folder_id, args.owner_email
            )
        else:
            operation = remove_legacy if args.command == "remove" else sanitize_legacy
            result = operation(args.database, args.lock_file, args.manifest, args.backup_receipt, args.credential_file)
            if args.command == "remove":
                result.update(migration_complete=False, next_step="sanitize")
    except Exception as error:
        # DuckDB/JSON/OS errors may embed input fragments: never print them.
        message = str(error) if isinstance(error, MigrationError) else type(error).__name__
        failure = {"completed": False, "reason": message}
        if isinstance(error, MigrationError) and error.rollback_path:
            failure.update(rollback_path=error.rollback_path, writers_must_remain_stopped=True)
        print(json.dumps(failure))
        return 2
    completed = result.get("migration_complete", True) if args.command == "sanitize" else True
    print(json.dumps({"completed": completed, **result}))
    return 0 if completed else 2


if __name__ == "__main__":
    raise SystemExit(main())
