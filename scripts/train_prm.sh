#!/usr/bin/env bash
# train_prm.sh - Train DeBERTa SQL-PRM model on generated pairwise dataset

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

export PYTHONPATH="$PROJECT_ROOT/pamo_sql:$PYTHONPATH"

PAIRS_FILE=${1:-"$PROJECT_ROOT/pamo_sql/data/processed/sql_prm_selector/pairwise_selector_train.jsonl"}
OUTPUT_DIR=${2:-"$PROJECT_ROOT/pamo_sql/artifacts/models/sql_prm_selector"}
MODEL_BASE=${3:-"microsoft/deberta-v3-base"}
EPOCHS=${4:-3}
BATCH_SIZE=${5:-8}

echo "=== Training SQL-PRM pairwise selector ==="
echo "Pairs file: $PAIRS_FILE"
echo "Output model path: $OUTPUT_DIR"
echo "Model base: $MODEL_BASE"
echo "Epochs: $EPOCHS"
echo "Batch size: $BATCH_SIZE"

python3 "$PROJECT_ROOT/pamo_sql/stage4_sql_prm_selection/train_sql_prm.py" \
  --pairs "$PAIRS_FILE" \
  --output_dir "$OUTPUT_DIR" \
  --model "$MODEL_BASE" \
  --epochs "$EPOCHS" \
  --batch_size "$BATCH_SIZE"

echo "=== SQL-PRM training complete! ==="
