#!/usr/bin/env bash
# run_preprocess.sh - Execute end-to-end preprocessing pipeline on BIRD

set -e

# Resolve script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

export PYTHONPATH="$PROJECT_ROOT/pamo_sql:$PYTHONPATH"

SPLIT=${1:-train}
INPUT_FILE=${2:-"$PROJECT_ROOT/pamo_sql/data/raw/bird/train.json"}

echo "=== Running PAMO-SQL Preprocessing ==="
echo "Project Root: $PROJECT_ROOT"
echo "Split: $SPLIT"
echo "Input: $INPUT_FILE"

python3 "$PROJECT_ROOT/pamo_sql/preprocess/run_all_preprocess.py" \
  --input "$INPUT_FILE" \
  --split "$SPLIT"

echo "=== Preprocessing completed! ==="
