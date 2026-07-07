#!/usr/bin/env bash
set -e

FLAKEIQ_DIR="$(cd "$(dirname "$0")" && pwd)"
RESULTS="$1"
if [ -z "$RESULTS" ]; then
  RESULTS="${FLAKEIQ_DIR}/flake-results.jsonl"
fi

echo "=== FlakeIQ Pipeline ==="
echo ""

# Step 1: Classify
echo "[1/2] Classifying failures..."
python3 "${FLAKEIQ_DIR}/classify.py" "$RESULTS"
echo ""

# Step 2: Dashboard
echo "[2/2] Starting dashboard..."
python3 "${FLAKEIQ_DIR}/dashboard.py" --port "${FLAKE_PORT:-8080}"
