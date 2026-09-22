#!/bin/bash
# Regenerate camp_fin_2026.db.gz from the local camp_fin_2026.db.
#
# The raw .db is gitignored; the .gz is what gets committed and what build.sh
# decompresses on the host. Run this after every data refresh, then:
#   git add camp_fin_2026.db.gz && git commit && git push
#
# Usage: ./compress-db.sh

set -euo pipefail
cd "$(dirname "$0")"

if [ ! -f camp_fin_2026.db ]; then
  echo "camp_fin_2026.db not found in $(pwd)" >&2
  exit 1
fi

# VACUUM into a temp copy first: reclaims free pages and lays the file out
# sequentially, which both shrinks it and compresses better. Leaves the
# working database untouched in case datasette is holding it open.
tmp="$(mktemp -t camp_fin_2026)"
rm -f "$tmp"
trap 'rm -f "$tmp"' EXIT

python3 - "$tmp" <<'PY'
import sqlite3, sys
con = sqlite3.connect("camp_fin_2026.db")
con.execute("VACUUM INTO ?", (sys.argv[1],))
con.close()
PY

gzip -9 -c "$tmp" > camp_fin_2026.db.gz.tmp
mv camp_fin_2026.db.gz.tmp camp_fin_2026.db.gz

# Never commit an archive that will not decompress on the host.
gzip -t camp_fin_2026.db.gz

printf "camp_fin_2026.db %s  ->  camp_fin_2026.db.gz %s\n" \
  "$(du -h camp_fin_2026.db | cut -f1 | tr -d ' ')" \
  "$(du -h camp_fin_2026.db.gz | cut -f1 | tr -d ' ')"
