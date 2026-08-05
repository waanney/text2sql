#!/bin/bash
#SBATCH --job-name=pamo_sql_eval
#SBATCH --output=logs/%x-%j.out
#SBATCH --error=logs/%x-%j.err
#SBATCH --gpus=a100_7g.80gb:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=12:00:00
#SBATCH --qos=short

# Create log directory if not exists
mkdir -p logs

# Activate Conda environment
source ~/.bashrc
conda activate pamo_sql

export PYTHONPATH=$(pwd)/pamo_sql:$PYTHONPATH

echo "=== Starting PAMO-SQL Evaluation Job ==="
nvidia-smi

# 1. Run dataset evaluation
python3 pamo_sql/pipelines/run_dataset.py \
  --dataset pamo_sql/data/raw/bird/dev.json \
  --bird_dir pamo_sql/data/raw/bird \
  --output_dir artifacts/evaluation

# 2. Evaluate Execution Accuracy
python3 pamo_sql/stage5_evaluation/evaluate_ex.py \
  --predicted_out artifacts/evaluation/evaluation_summary.json \
  --gold_path pamo_sql/data/raw/bird/dev.json \
  --db_dir pamo_sql/data/raw/bird/dev_databases

echo "=== Job Finished ==="
