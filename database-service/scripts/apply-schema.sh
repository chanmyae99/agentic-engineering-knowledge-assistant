#!/usr/bin/env bash

set -euo pipefail

CONTAINER_NAME="${CONTAINER_NAME:-knowledge-assistant-db}"
POSTGRES_DB="${POSTGRES_DB:-knowledge_assistant}"
POSTGRES_USER="${POSTGRES_USER:-knowledge_admin}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
SCHEMA_DIRECTORY="${PROJECT_ROOT}/database-service/schema"

if [[ ! -d "${SCHEMA_DIRECTORY}" ]]; then
    echo "Schema directory not found: ${SCHEMA_DIRECTORY}"
    exit 1
fi

echo "Checking PostgreSQL container..."

if [[ "$(docker inspect -f '{{.State.Running}}' "${CONTAINER_NAME}" 2>/dev/null)" != "true" ]]; then
    echo "Container '${CONTAINER_NAME}' is not running."
    exit 1
fi

echo "Copying schema files into the container..."

docker exec "${CONTAINER_NAME}" \
    rm -rf /tmp/knowledge-assistant-schema

docker cp \
    "${SCHEMA_DIRECTORY}" \
    "${CONTAINER_NAME}:/tmp/knowledge-assistant-schema"

echo "Applying database schema..."

docker exec \
    -e PGPASSWORD="${POSTGRES_PASSWORD:-}" \
    "${CONTAINER_NAME}" \
    psql \
    -v ON_ERROR_STOP=1 \
    -U "${POSTGRES_USER}" \
    -d "${POSTGRES_DB}" \
    -f /tmp/knowledge-assistant-schema/05-apply-schema.sql

echo
echo "Database schema applied successfully."