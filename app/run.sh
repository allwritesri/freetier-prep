#!/usr/bin/env bash
# One command to run (./run.sh) or test (./run.sh test) freetier-prep dev mode.
set -euo pipefail
cd "$(dirname "$0")"

python3 -m pip install -q -r requirements.txt

if [ "${1:-serve}" = "test" ]; then
  exec python3 -m pytest tests/ -q
fi

echo "freetier-prep dev mode → http://localhost:${PORT:-8000}"
exec python3 -m uvicorn freetier_prep.main:app --host 0.0.0.0 --port "${PORT:-8000}"
