#!/usr/bin/env python3
"""
Database inspection helper

Shows tables, row counts (volumetrias) and a few example rows for each table
for the project's SQLite databases under `backend/data`.

Usage:
  python scripts/db/db_inspect.py                 # inspeciona ambos os DBs (podcast_database + nerdcasts)
  python scripts/db/db_inspect.py --db path/to/db  # inspeciona um DB específico
"""
from pathlib import Path
import sqlite3
import json
import argparse

DEFAULT_DB_DIR = Path(__file__).resolve().parents[2] / 'backend' / 'data'
DEFAULT_DBS = [DEFAULT_DB_DIR / 'podcast_database.db', DEFAULT_DB_DIR / 'nerdcasts.db']


def inspect_db(db_path: Path, sample_limit: int = 3):
    print(f"\nDB: {db_path}")
    if not db_path.exists():
        print("  NOT FOUND")
        return

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # List tables
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in cur.fetchall()]
    print(f"  Tables: {len(tables)}")

    for t in tables:
        if t.startswith('sqlite_'):
            continue
        try:
            cur.execute(f'SELECT COUNT(*) FROM "{t}"')
            count = cur.fetchone()[0]
        except Exception as e:
            count = f'ERROR: {e}'

        # columns
        cur.execute(f"PRAGMA table_info('{t}')")
        cols = [r[1] for r in cur.fetchall()]

        print(f"  - {t}: {count} rows, columns={cols}")

        # sample rows
        try:
            cur.execute(f'SELECT * FROM "{t}" LIMIT {sample_limit}')
            rows = [dict(r) for r in cur.fetchall()]
        except Exception as e:
            print(f"    ERROR reading rows: {e}")
            rows = []

        if not rows:
            print("    (no rows)")
            continue

        print("    Examples:")
        for row in rows:
            # pick a few informative fields if present
            prefer = ['id', 'title', 'title_original', 'filename', 'podcast_source', 'published_date', 'created_at']
            out = {k: row.get(k) for k in prefer if k in row}
            if not out:
                # fallback: show up to first 4 columns
                for k in cols[:4]:
                    out[k] = row.get(k)
            print('     ', json.dumps(out, ensure_ascii=False))

    conn.close()


def main():
    parser = argparse.ArgumentParser(description='Inspect SQLite DBs and show tables/volumes/examples')
    parser.add_argument('--db', type=str, help='Path to a specific DB file')
    parser.add_argument('--samples', type=int, default=3, help='Number of sample rows per table')

    args = parser.parse_args()

    dbs = []
    if args.db:
        dbs = [Path(args.db)]
    else:
        dbs = DEFAULT_DBS

    for db in dbs:
        inspect_db(db, sample_limit=args.samples)


if __name__ == '__main__':
    main()
