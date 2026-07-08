import os
import sys
import argparse
from pathlib import Path

# Insert project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.io_utils import load_jsonl
from common.logging_utils import log_event
from preprocess.00_validate_bird import validate_bird_file
from preprocess.01_profile_database import profile_database_by_id
from preprocess.02_execute_gold_sql import execute_gold_sql
from preprocess.03_parse_gold_sql import parse_gold_sqls
from preprocess.04_build_schema_ranker_data import build_schema_ranker_data
from preprocess.05_build_generator_sft_data import build_generator_sft_data
from preprocess.06_generate_candidate_sql import generate_candidate_sqls
from preprocess.08_execute_candidates import execute_candidates
from preprocess.09_build_sql_prm_data import build_sql_prm_data
from preprocess.10_build_rl_rollout_pool import build_rl_rollout_pool


def run_all_preprocess(input_path, split="train"):
    log_event("INFO", f"=== Starting end-to-end preprocess pipeline for split: {split} ===")

    # Step 00: Validate BIRD files
    valid_out, invalid_out = validate_bird_file(input_path, split)

    # Gather unique db_ids
    valid_samples = load_jsonl(valid_out)
    db_ids = set(s["db_id"] for s in valid_samples)
    log_event("INFO", f"Found {len(db_ids)} unique databases in valid samples.")

    # Step 01: Profile each database
    for db_id in db_ids:
        prof_out = Path(__file__).resolve().parent.parent / "data" / "processed" / "metadata" / db_id / "column_profiles.json"
        profile_database_by_id(db_id, str(prof_out))

    # Step 02: Execute Gold SQL
    execute_gold_sql(valid_out, split)

    # Step 03: Parse Gold SQL
    parse_gold_sqls(valid_out, split)

    # Step 04: Build Schema-Ranker Data
    build_schema_ranker_data(valid_out, split)

    # Step 05: Build Generator SFT Data
    build_generator_sft_data(valid_out, split)

    # Step 06: Generate Candidate SQL
    generate_candidate_sqls(valid_out, split)

    # Step 08: Execute Candidates
    execute_candidates(valid_out, split)

    # Step 09: Build SQL-PRM Data
    build_sql_prm_data(valid_out, split)

    # Step 10: Build RL Rollout Pool
    build_rl_rollout_pool(valid_out, split)

    log_event("INFO", f"=== End-to-end preprocess pipeline finished successfully for split: {split} ===")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/raw/bird/train.json")
    parser.add_argument("--split", default="train")
    args = parser.parse_args()

    run_all_preprocess(args.input, args.split)
