# PAMO-SQL

PAMO-SQL is a profile-aware modular framework for Text-to-SQL research and ablation experiments.

## Project Structure

- `common/`: Schema definitions and LLM API client wrapper.
- `configs/`: Experiment config templates, including ablation settings.
- `stage0_metadata/`: Offline metadata profiling and preprocessing tools.
- `stage1_understanding/`: Profile-aware context retrieval and schema ranking.
- `stage2_generation/`: Multi-generator SQL candidate generation (reasoning, ICL, metadata-constrained, and simple).
- `stage3_execution_repair/`: SQLite execution and feedback-driven correction loops.
- `stage4_selection/`: Multi-factor candidate evaluation and final selection.
- `stage5_evaluation/`: Accuracy, latency, cost, and ablation runner metrics.
- `pipelines/`: End-to-end question and dataset pipeline orchestrators.

## Getting Started

1. Install requirements:
   ```bash
   pip install -r pamo_sql/requirements.txt
   ```

2. Configure environment variables in a `.env` file:
   ```env
   OPENAI_API_KEY="your-api-key"
   OPENAI_MODEL="gpt-4o-mini"
   ```

3. Run a test dry-run:
   ```bash
   python3 pamo_sql/pipelines/run_single_question.py
   ```
