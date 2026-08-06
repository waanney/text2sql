# PAMO-SQL v2: Profile-Aware & Execution-Guided Text-to-SQL Framework

PAMO-SQL v2 is an advanced, profile-aware modular framework designed for high-accuracy Text-to-SQL generation on the BIRD benchmark. It incorporates **Rich DDL Data Profiling**, **Value-based Schema Linking**, **Multi-Generator Candidate Generation**, **Execution-Guided Self-Correction**, and **SQL-PRM Selection**.

---

## 📁 Directory Structure

- `pamo_sql/stage0_metadata/`: Offline metadata profiling and schema enrichment.
- `pamo_sql/stage1_understanding/`: Profile-aware context retrieval, schema ranking, and value linking.
- `pamo_sql/stage2_generation/`: Multi-generator SQL candidate generation (Reasoning, ICL, Metadata-constrained, Evidence-focused, Join-focused, Simple).
- `pamo_sql/stage3_execution_repair/`: SQLite execution and feedback-driven repair loops (handling syntax errors and zero-row empty outputs).
- `pamo_sql/stage4_sql_prm_selection/`: SQL Process Reward Model (PRM) & Pairwise Tournament Selection.
- `pamo_sql/stage4_5_hardcase_refinement/`: Hard-case query detection and MCTS refinement.
- `pamo_sql/stage5_evaluation/`: Official BIRD Execution Accuracy (EX) evaluation.
- `pamo_sql/pipelines/`: Single question and full dataset orchestrators.
- `scripts/run_pamo.slurm`: SLURM batch execution script for HPC cluster nodes.

---

## 🖥️ Running on HPC Cluster (Evaluation & Training)

### 1. Environment Setup

Activate the Conda environment and install dependencies:

```bash
conda activate pamo_sql
pip install -r pamo_sql/requirements.txt
```

---

### 2. Running Full Evaluation via SLURM (Recommended)

Submit the evaluation job to the SLURM cluster (configured for NVIDIA A100 GPU and `Qwen/Qwen2.5-Coder-14B-Instruct`):

```bash
# Submit evaluation job to GPU queue
sbatch scripts/run_pamo.slurm
```

To adjust the evaluation sample size or LLM model, edit `scripts/run_pamo.slurm`:
- Change `--limit 30` to run on 30 questions (or remove `--limit` for full BIRD dev set).
- Modify `export LOCAL_MODEL_NAME="Qwen/Qwen2.5-Coder-14B-Instruct"`.

---

### 3. Monitoring & Managing SLURM Jobs

- **Check job status:**
  ```bash
  squeue -u $USER
  ```

- **View real-time evaluation logs:**
  ```bash
  tail -f logs/pamo_sql_eval-*.out
  ```

- **Cancel a running job:**
  ```bash
  scancel <JOB_ID>
  ```

---

### 4. Interactive Execution (No Queueing)

If you are already inside an interactive GPU node or `tmux`/`screen` session:

```bash
export PYTHONPATH=$(pwd)/pamo_sql:$PYTHONPATH
export USE_LOCAL_LLM=1
export LOCAL_MODEL_NAME="Qwen/Qwen2.5-Coder-14B-Instruct"

# Step 1: Run pipeline generation & execution
python3 pamo_sql/pipelines/run_dataset.py \
  --dataset pamo_sql/data/raw/bird/dev.json \
  --bird_dir pamo_sql/data/raw/bird \
  --output_dir artifacts/evaluation \
  --limit 30

# Step 2: Calculate Official BIRD Execution Accuracy (EX)
python3 pamo_sql/stage5_evaluation/evaluate_ex.py \
  --predicted_out artifacts/evaluation/evaluation_summary.json \
  --gold_path pamo_sql/data/raw/bird/dev.json \
  --db_dir pamo_sql/data/raw/bird/dev_databases
```

---

### 5. Re-evaluating Saved Predictions

To re-compute official EX metrics on existing predictions without re-running LLM generation:

```bash
python3 pamo_sql/stage5_evaluation/evaluate_ex.py \
  --predicted_out artifacts/evaluation/evaluation_summary.json \
  --gold_path pamo_sql/data/raw/bird/dev.json \
  --db_dir pamo_sql/data/raw/bird/dev_databases
```

---

### 6. Training SQL-PRM (Process Reward Model)

To train the Process Reward Model for Stage 4 candidate selection:

```bash
# Build pairwise training dataset from evaluation artifacts
python3 pamo_sql/stage4_sql_prm_selection/build_pairwise_dataset.py

# Train DeBERTa / Transformer reward model
python3 pamo_sql/stage4_sql_prm_selection/train_sql_prm.py
```
