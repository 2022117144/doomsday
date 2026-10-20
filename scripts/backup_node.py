#!/usr/bin/env python3
"""
Atomic Hot Backup Utility for Doomsday Seed Node.
Safely snapshots SQLite ledger (data/doomsday.db), pool_state.json,
node wallets, and bridge relayer state without locking or stopping the node.
"""
import glob
import os
import shutil
import sqlite3
import tarfile
import time
from datetime import datetime, timezone

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BACKUP_ROOT = os.path.join(BASE_DIR, "backups")
LATEST_DIR = os.path.join(BACKUP_ROOT, "latest")
ARCHIVE_DIR = os.path.join(BACKUP_ROOT, "archive")
MAX_ARCHIVES = 72  # Keep last 72 snapshots (3 days of hourly snapshots)


def run_backup():
    os.makedirs(LATEST_DIR, exist_ok=True)
    os.makedirs(ARCHIVE_DIR, exist_ok=True)

    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")

    # 1. Atomic SQLite online backup of data/doomsday.db
    src_db = os.path.join(BASE_DIR, "data", "doomsday.db")
    dst_db = os.path.join(LATEST_DIR, "doomsday.db")
    block_count = 0
    if os.path.exists(src_db):
        src_conn = sqlite3.connect(src_db)
        dst_conn = sqlite3.connect(dst_db)
        with dst_conn:
            src_conn.backup(dst_conn)
        cur = dst_conn.cursor()
        cur.execute("SELECT COUNT(*) FROM blocks")
        block_count = cur.fetchone()[0]
        dst_conn.close()
        src_conn.close()

    # 2. Copy critical JSON state files
    state_files = [
        ("data/pool_state.json", "pool_state.json"),
        ("faucet_wallet.json", "faucet_wallet.json"),
        ("pool_wallet.json", "pool_wallet.json"),
        ("bridge/relayer_state.json", "relayer_state.json"),
    ]
    for rel_src, dst_name in state_files:
        full_src = os.path.join(BASE_DIR, rel_src)
        if os.path.exists(full_src):
            shutil.copy2(full_src, os.path.join(LATEST_DIR, dst_name))

    # 3. Write backup manifest
    manifest_path = os.path.join(LATEST_DIR, "manifest.txt")
    with open(manifest_path, "w", encoding="utf-8") as f:
        f.write(f"timestamp_utc={ts}\n")
        f.write(f"blocks_count={block_count}\n")

    # 4. Create compressed archive
    archive_path = os.path.join(ARCHIVE_DIR, f"doomsday-backup-{ts}.tar.gz")
    with tarfile.open(archive_path, "w:gz") as tar:
        tar.add(LATEST_DIR, arcname=f"doomsday-backup-{ts}")

    # 5. Rotate old archives
    archives = sorted(glob.glob(os.path.join(ARCHIVE_DIR, "doomsday-backup-*.tar.gz")))
    if len(archives) > MAX_ARCHIVES:
        for old_file in archives[:-MAX_ARCHIVES]:
            try:
                os.remove(old_file)
            except OSError:
                pass

    print(f"[Backup] OK ({ts} UTC) — {block_count} blocks archived to {archive_path}")


if __name__ == "__main__":
    run_backup()
