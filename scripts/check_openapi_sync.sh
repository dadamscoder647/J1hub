#!/usr/bin/env bash
set -euo pipefail

BASE_REF="${1:-}"
if [[ -z "$BASE_REF" ]]; then
  if [[ -n "${GITHUB_BASE_REF:-}" ]]; then
    BASE_REF="origin/${GITHUB_BASE_REF}"
  elif [[ -n "${GITHUB_EVENT_BEFORE:-}" && "${GITHUB_EVENT_BEFORE}" != "0000000000000000000000000000000000000000" ]]; then
    BASE_REF="${GITHUB_EVENT_BEFORE}"
  else
    echo "No base ref available; skipping OpenAPI sync check."
    exit 0
  fi
fi

if ! git rev-parse --verify "$BASE_REF" >/dev/null 2>&1; then
  git fetch --all --prune --quiet || true
fi

CHANGED_FILES=$(git diff --name-only "$BASE_REF"...HEAD)
if [[ -z "$CHANGED_FILES" ]]; then
  echo "No changed files detected."
  exit 0
fi

if echo "$CHANGED_FILES" | rg -q '^(routes/.*\.py|app\.py)$'; then
  if ! echo "$CHANGED_FILES" | rg -q '^(openapi\.yaml|docs/openapi\.yaml)$'; then
    echo "API handlers changed without updating OpenAPI spec (openapi.yaml or docs/openapi.yaml)."
    exit 1
  fi
fi

echo "OpenAPI sync check passed."
