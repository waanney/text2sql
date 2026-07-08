#!/usr/bin/env bash
# setup_docker.sh - Setup and build Docker images, run the main services, and log view.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Switch to the folder containing docker-compose.yml
cd "$PROJECT_ROOT/pamo_sql"

echo "=== Building PAMO-SQL Docker images ==="
docker compose build

echo "=== Starting log viewer service (Dozzle) ==="
docker compose --profile monitoring up -d log-viewer

echo "=== Run single question dry-run inside Docker ==="
docker compose run --rm pamo-sql

echo "=== All done. Access logs visually at http://localhost:9999 ==="
