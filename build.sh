#!/bin/bash
# Deploy-time build step for Railway (or any Python host).
#
# camp_fin_2026.db is committed gzipped: ~52 MB raw, under 10 MB compressed,
# which keeps the repo well clear of GitHub's 50 MB file warning without
# dropping any tables. Decompress it here so datasette can open it.

set -euo pipefail

cd "$(dirname "$0")"

echo "==> Installing dependencies"
pip install -r requirements.txt

echo "==> Decompressing camp_fin_2026.db"
gzip -dc camp_fin_2026.db.gz > camp_fin_2026.db
printf "    camp_fin_2026.db (%s)\n" "$(du -h camp_fin_2026.db | cut -f1 | tr -d ' ')"

# Fail the build loudly rather than serving a truncated database. Uses python's
# bundled sqlite3 module, since the sqlite3 CLI is not guaranteed on the host.
echo "==> Verifying"
python3 - <<'PY'
import sqlite3, sys

con = sqlite3.connect("camp_fin_2026.db")
try:
    tables = [r[0] for r in con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )]
except sqlite3.Error as e:
    sys.exit(f"    camp_fin_2026.db is unreadable: {e}")

if not tables:
    sys.exit("    camp_fin_2026.db has no tables")

for t in tables:
    n = con.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
    if not n:
        sys.exit(f"    {t} is empty")
    print(f"    {t}: {n:,} rows")
con.close()
PY
