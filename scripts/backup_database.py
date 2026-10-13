"""Create a database backup and verify its basic integrity.

Usage: python scripts/backup_database.py [/path/to/backup-directory]
For PostgreSQL, pg_dump and pg_restore must be installed. For SQLite, use the
SQLite online backup API so WAL-mode databases are copied consistently.
"""
from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote

url = os.getenv("DATABASE_URL", "sqlite:///./smart_market.db")
out = Path(sys.argv[1] if len(sys.argv) > 1 else "./backups")
out.mkdir(parents=True, exist_ok=True)
stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

if url.startswith(("postgresql://", "postgres://", "postgresql+psycopg://", "postgresql+psycopg2://")):
    # pg_dump accepts standard PostgreSQL URIs; normalize SQLAlchemy driver suffixes.
    pg_url = url.replace("postgresql+psycopg2://", "postgresql://", 1).replace("postgresql+psycopg://", "postgresql://", 1)
    target = out / f"smart_market_{stamp}.dump"
    subprocess.run(["pg_dump", "--format=custom", "--file", str(target), pg_url], check=True)
    # Listing the archive validates that pg_restore can read its catalog.
    subprocess.run(["pg_restore", "--list", str(target)], check=True, stdout=subprocess.DEVNULL)
else:
    prefix = "sqlite:///"
    if not url.startswith(prefix):
        raise SystemExit("Unsupported DATABASE_URL scheme; expected SQLite or PostgreSQL.")
    source = Path(unquote(url[len(prefix):]))
    if not source.is_absolute():
        source = Path.cwd() / source
    if not source.is_file():
        raise SystemExit(f"SQLite database file not found: {source}")
    target = out / f"smart_market_{stamp}.db"
    source_conn = sqlite3.connect(f"file:{source}?mode=ro", uri=True)
    target_conn = sqlite3.connect(target)
    try:
        source_conn.backup(target_conn)
        check = target_conn.execute("PRAGMA quick_check").fetchone()
        if not check or check[0] != "ok":
            raise RuntimeError(f"SQLite backup integrity check failed: {check!r}")
    except Exception:
        target_conn.close()
        source_conn.close()
        target.unlink(missing_ok=True)
        raise
    finally:
        try:
            target_conn.close()
        except Exception:
            pass
        try:
            source_conn.close()
        except Exception:
            pass

print(f"Backup created and integrity-checked: {target}")
