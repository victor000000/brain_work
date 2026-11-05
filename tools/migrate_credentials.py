"""Export legacy database credentials, then remove them after private backup.

This tool never stops the explorer. It requires its exclusive writer lock.
Credential values are written only to private files and never printed.
"""

import argparse
import json

from core.credential_migration import export_legacy, remove_legacy


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    export = commands.add_parser("export")
    export.add_argument("--database", required=True)
    export.add_argument("--lock-file", required=True)
    export.add_argument("--output-directory", required=True)
    export.add_argument("--drive-folder-id", required=True)
    export.add_argument("--owner-email", required=True)
    remove = commands.add_parser("remove")
    remove.add_argument("--database", required=True)
    remove.add_argument("--lock-file", required=True)
    remove.add_argument("--manifest", required=True)
    remove.add_argument("--backup-receipt")
    remove.add_argument("--credential-file")
    args = parser.parse_args(argv)
    try:
        if args.command == "export":
            result = export_legacy(
                args.database, args.lock_file, args.output_directory, args.drive_folder_id, args.owner_email
            )
        else:
            result = remove_legacy(
                args.database, args.lock_file, args.manifest, args.backup_receipt, args.credential_file
            )
    except Exception as error:
        # DuckDB/JSON/OS errors may embed input fragments: never print them.
        from core.credential_migration import MigrationError

        message = str(error) if isinstance(error, MigrationError) else type(error).__name__
        print(json.dumps({"completed": False, "reason": message}))
        return 2
    print(json.dumps({"completed": True, **result}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
