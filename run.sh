#!/usr/bin/env bash
set -e

FLAKEIQ_DIR="$(cd "$(dirname "$0")" && pwd)"
RESULTS="$1"
if [ -z "$RESULTS" ]; then
  RESULTS="flake-results.jsonl"
fi

echo "=== FlakeIQ Pipeline ==="
echo ""

# Step 1: Classify
echo "[1/2] Classifying failures from $(basename "$RESULTS")..."
python3 "${FLAKEIQ_DIR}/classify.py" "$RESULTS"
echo ""

# Step 2: Dashboard
echo "[2/2] Starting dashboard..."
echo "  Use --seed to view seed data, --open to auto-launch browser"
python3 "${FLAKEIQ_DIR}/dashboard.py" --port "${FLAKE_PORT:-8080}" --open
