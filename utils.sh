#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ -f "$ROOT_DIR/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT_DIR/.env"
  set +a
fi

BACKEND_HOST="${BACKEND_HOST:-127.0.0.1}"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_HOST="${FRONTEND_HOST:-127.0.0.1}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.yml}"
COMPOSE_DETACH="${COMPOSE_DETACH:-0}"

run_backend() {
  ensure_port_available "$BACKEND_HOST" "$BACKEND_PORT" "backend"
  cd "$ROOT_DIR"
  compose_up backend
}

run_frontend() {
  ensure_port_available "$FRONTEND_HOST" "$FRONTEND_PORT" "frontend"
  cd "$ROOT_DIR"
  compose_up --no-deps frontend
}

run_all() {
  ensure_port_available "$BACKEND_HOST" "$BACKEND_PORT" "backend"
  ensure_port_available "$FRONTEND_HOST" "$FRONTEND_PORT" "frontend"
  cd "$ROOT_DIR"
  compose_up
}

run_database() {
  cd "$ROOT_DIR"
  compose_up postgres
}

stop_all() {
  cd "$ROOT_DIR"
  docker compose -f "$COMPOSE_FILE" down
}

show_logs() {
  cd "$ROOT_DIR"
  docker compose -f "$COMPOSE_FILE" logs -f "${2:-}"
}

compose_up() {
  if [[ "$COMPOSE_DETACH" == "1" ]]; then
    docker compose -f "$COMPOSE_FILE" up --build -d "$@"
  else
    docker compose -f "$COMPOSE_FILE" up --build "$@"
  fi
}

ensure_port_available() {
  local host="$1"
  local port="$2"
  local service_name="$3"

  if ss -ltn "( sport = :$port )" | grep -q LISTEN; then
    echo "Port $port is already in use. Stop the existing $service_name service or change ${service_name^^}_PORT in .env."
    exit 1
  fi
}

case "${1:-}" in
  db)
    run_database
    ;;
  backend)
    run_backend
    ;;
  frontend)
    run_frontend
    ;;
  dev)
    run_all
    ;;
  stop)
    stop_all
    ;;
  logs)
    show_logs "$@"
    ;;
  *)
    echo "Usage: ./utils.sh {db|backend|frontend|dev|stop|logs [service]}"
    exit 1
    ;;
esac
