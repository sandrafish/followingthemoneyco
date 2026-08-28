#!/bin/bash
# Preview the site locally, exactly as it runs on Railway.
#
# The custom landing page, /about and /sql only exist because of
# --template-dir, and the home page's table list only exists because of
# --plugins-dir, so a bare `datasette camp_fin_2026.db` shows none of them.
# This runs the same command the Procfile does, bound to localhost.
#
# Usage: ./serve.sh [port]        (default 8010; Ctrl-C to stop)

set -euo pipefail
cd "$(dirname "$0")"

PORT="${1:-8010}"

if [ ! -f camp_fin_2026.db ]; then
  echo "camp_fin_2026.db not found in $(pwd)" >&2
  exit 1
fi

# Bail out early on a busy port. Without this the bind fails after startup and
# another server on that port answers instead, which looks like broken pages.
if lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "port $PORT is already in use -- try: ./serve.sh $((PORT + 1))" >&2
  exit 1
fi

# Prefer the checked-out virtualenv so the pinned Datasette is what runs.
if [ -x .venv/bin/datasette ]; then
  DATASETTE=.venv/bin/datasette
elif command -v datasette >/dev/null 2>&1; then
  DATASETTE=datasette
else
  echo "datasette not found -- try: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt" >&2
  exit 1
fi

echo
echo "  home       http://127.0.0.1:$PORT/"
echo "  using sql  http://127.0.0.1:$PORT/sql"
echo "  more info  http://127.0.0.1:$PORT/about"
echo "  raw data   http://127.0.0.1:$PORT/camp_fin_2026"
echo

# Same flags as the Procfile, minus the 0.0.0.0 bind Railway needs.
exec "$DATASETTE" camp_fin_2026.db \
  --host 127.0.0.1 --port "$PORT" \
  --plugins-dir plugins \
  --template-dir templates \
  --metadata metadata.json \
  --reload
