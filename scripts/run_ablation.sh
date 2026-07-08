#!/usr/bin/env bash
# run_ablation.sh - Run ablation experiments on the BIRD validation/dev split

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

export PYTHONPATH="$PROJECT_ROOT/pamo_sql:$PYTHONPATH"

LIMIT=${1:-5}
DATASET=${2:-"$PROJECT_ROOT/pamo_sql/data/raw/bird/dev.json"}

echo "=== Running PAMO-SQL Ablation Experiments ==="
echo "Dataset: $DATASET"
echo "Limit: $LIMIT"

python3 "$PROJECT_ROOT/pamo_sql/pipelines/run_ablation.py" \
  --ablation_yaml "$PROJECT_ROOT/pamo_sql/configs/experiment_ablation.yaml" \
  --dataset "$DATASET" \
  --bird_dir "$PROJECT_ROOT/pamo_sql/data/raw/bird" \
  --output_dir "$PROJECT_ROOT/pamo_sql/artifacts/ablation" \
  --limit "$LIMIT"

echo "=== Ablation experiments completed! ==="
