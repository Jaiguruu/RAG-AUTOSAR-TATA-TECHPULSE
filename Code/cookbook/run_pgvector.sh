#!/usr/bin/env sh
set -eu

POSTGRES_DB="${POSTGRES_DB:-ai}"
POSTGRES_USER="${POSTGRES_USER:-ai}"
: "${POSTGRES_PASSWORD:?Set POSTGRES_PASSWORD in your environment (copy .env.example to .env and source it).}"

if docker ps -a --format '{{.Names}}' | grep -qx 'pgvector'; then
  echo "Container 'pgvector' already exists. Start it with: docker start pgvector"
  exit 0
fi

docker run -d \
  --name pgvector \
  -e "POSTGRES_DB=${POSTGRES_DB}" \
  -e "POSTGRES_USER=${POSTGRES_USER}" \
  -e "POSTGRES_PASSWORD=${POSTGRES_PASSWORD}" \
  -e PGDATA=/var/lib/postgresql/data/pgdata \
  -v pgvolume:/var/lib/postgresql/data \
  -p 127.0.0.1:5532:5432 \
  phidata/pgvector:16
