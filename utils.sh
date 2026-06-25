#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_HOST="${BACKEND_HOST:-127.0.0.1}"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_HOST="${FRONTEND_HOST:-127.0.0.1}"

run_backend() {
  cd "$ROOT_DIR"
  "$ROOT_DIR/.venv/bin/python" -m uvicorn apps.backend.app:app \
    --host "$BACKEND_HOST" \
    --port "$BACKEND_PORT" \
    --reload
}

run_frontend() {
  cd "$ROOT_DIR/apps/frontend"
  npm run dev -- --host "$FRONTEND_HOST"
}

run_all() {
  run_backend &
  BACKEND_PID=$!

  run_frontend &
  FRONTEND_PID=$!

  trap 'kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true' EXIT INT TERM
  wait "$BACKEND_PID" "$FRONTEND_PID"
}

case "${1:-}" in
  backend)
    run_backend
    ;;
  frontend)
    run_frontend
    ;;
  dev)
    run_all
    ;;
  *)
    echo "Usage: ./utils.sh {backend|frontend|dev}"
    exit 1
    ;;
esac
