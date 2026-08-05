#!/bin/bash
#SBATCH --job-name=pamo_sql_eval
#SBATCH --output=logs/%x-%j.out
#SBATCH --error=logs/%x-%j.err
#SBATCH --gpus=a100_3g.40gb:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=12:00:00
#SBATCH --qos=short

# Create log directory if not exists
mkdir -p logs

# Initialize & activate Conda environment safely in non-interactive batch job
CONDA_BASE=$(conda info --base 2>/dev/null || echo "$HOME/miniconda3")
if [ -f "$CONDA_BASE/etc/profile.d/conda.sh" ]; then
    source "$CONDA_BASE/etc/profile.d/conda.sh"
fi
conda activate pamo_sql

export PYTHONPATH=$(pwd)/pamo_sql:$PYTHONPATH
python3 -c "import accelerate" 2>/dev/null || pip install --quiet --user accelerate

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
