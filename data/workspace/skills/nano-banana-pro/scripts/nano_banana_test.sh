#!/bin/bash
set -e -E

SOCKET_PATH="${LOCAL_SKILL_SERVER_SOCKET:-/run/skill-server/api.sock}"
SERVER_URL="${LOCAL_SKILL_SERVER_URL:-}"
REQUEST_PATH="/v1/nano-banana/generate"
TOKEN_HEADER=()

if [ -n "${SKILL_SERVER_SERVICE_TOKEN:-}" ]; then
  TOKEN_HEADER=(-H "x-skill-service-token: ${SKILL_SERVER_SERVICE_TOKEN}")
fi

if [ -n "${SERVER_URL}" ]; then
  curl -v \
    -X POST \
    "${TOKEN_HEADER[@]}" \
    -F "prompt=banana illust" \
    -F "resolution=1K" \
    -F "filename_hint=banana.png" \
    "${SERVER_URL%/}${REQUEST_PATH}"
else
  curl -v \
    --unix-socket "${SOCKET_PATH}" \
    -X POST \
    "${TOKEN_HEADER[@]}" \
    -F "prompt=banana illust" \
    -F "resolution=1K" \
    -F "filename_hint=banana.png" \
    "http://skill-server${REQUEST_PATH}"
fi

