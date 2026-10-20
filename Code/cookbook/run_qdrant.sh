#!/usr/bin/env sh
set -eu

: "${QDRANT_API_KEY:?Set QDRANT_API_KEY in your environment (copy .env.example to .env and source it).}"

if docker ps -a --format '{{.Names}}' | grep -qx 'qdrant'; then
  echo "Container 'qdrant' already exists. Start it with: docker start qdrant"
  exit 0
fi

docker run -d \
  --name qdrant \
  -p 127.0.0.1:6333:6333 \
  -p 127.0.0.1:6334:6334 \
  -e "QDRANT__SERVICE__API_KEY=${QDRANT_API_KEY}" \
  -v qdrant_storage:/qdrant/storage \
  qdrant/qdrant
