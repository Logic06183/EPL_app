#!/usr/bin/env bash
# Run the whole app offline against the mock FPL API.
#   scripts/demo.sh up     # mock FPL :8090, API :8001, SPA :3000 (background, logs in .demo/)
#   scripts/demo.sh down
set -euo pipefail
cd "$(dirname "$0")/.."
PY="${PYTHON:-.venv/bin/python}"
mkdir -p .demo

up() {
  "$PY" scripts/mock_fpl.py --port 8090 > .demo/mock.log 2>&1 & echo $! > .demo/mock.pid
  FPL_API_BASE=http://localhost:8090/api LOG_FORMAT=text \
    "$PY" -m uvicorn app.main:app --port 8001 > .demo/api.log 2>&1 & echo $! > .demo/api.pid
  "$PY" -m http.server 3000 --directory frontend > .demo/spa.log 2>&1 & echo $! > .demo/spa.pid
  for _ in $(seq 1 60); do
    if curl -fsS http://localhost:8001/ping >/dev/null 2>&1; then
      echo "Demo running: http://localhost:3000  (API http://localhost:8001/docs, team id 1)"
      return 0
    fi
    sleep 1
  done
  echo "API did not start — see .demo/api.log" >&2
  return 1
}

down() {
  for f in .demo/*.pid; do
    [[ -f "$f" ]] || continue
    kill "$(cat "$f")" 2>/dev/null || true
    rm -f "$f"
  done
}

case "${1:-up}" in
  up) up ;;
  down) down ;;
  *) echo "usage: $0 up|down" >&2; exit 2 ;;
esac
