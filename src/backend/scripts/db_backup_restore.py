"""SQLite backup/restore helper for OCI Cost Manager."""

from __future__ import annotations

import argparse
import shutil
from datetime import UTC, datetime
from pathlib import Path


def _default_db_path() -> Path:
    return Path(__file__).resolve().parents[1] / "oci_cost_manager.db"


def backup(db_path: Path, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    out_file = out_dir / f"oci_cost_manager_{stamp}.db"
    shutil.copy2(db_path, out_file)
    return out_file


def restore(backup_file: Path, db_path: Path) -> Path:
    if not backup_file.exists():
        raise FileNotFoundError(f"Backup file not found: {backup_file}")
    db_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(backup_file, db_path)
    return db_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Backup/restore OCI Cost Manager SQLite DB")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_backup = sub.add_parser("backup", help="Create a timestamped DB backup")
    p_backup.add_argument("--db", default=str(_default_db_path()))
    p_backup.add_argument("--out", default=str((Path.cwd() / "backups").resolve()))

    p_restore = sub.add_parser("restore", help="Restore DB from backup file")
    p_restore.add_argument("--file", required=True)
    p_restore.add_argument("--db", default=str(_default_db_path()))

    args = parser.parse_args()
    if args.cmd == "backup":
        path = backup(Path(args.db), Path(args.out))
        print(f"BACKUP_OK {path}")
        return 0
    if args.cmd == "restore":
        path = restore(Path(args.file), Path(args.db))
        print(f"RESTORE_OK {path}")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

