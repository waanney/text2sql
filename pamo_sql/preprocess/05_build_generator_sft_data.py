import os
import sys
import argparse
from pathlib import Path

# Insert project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.io_utils import load_jsonl, save_jsonl
from common.bird_utils import resolve_db_path
from common.logging_utils import log_event


def get_mock_ddl(db_id, profiles):
    """Generate DDL schema representation from column profiles."""
    tables = {}
    for p in profiles:
        t = p["table_name"]
        c = p["column_name"]
        dt = p.get("declared_type", "TEXT")
        if t not in tables:
            tables[t] = []
        tables[t].append(f'  "{c}" {dt}')
        
    ddl_parts = []
    for t, cols in tables.items():
        ddl_parts.append(f"CREATE TABLE {t} (\n" + ",\n".join(cols) + "\n);")
    return "\n".join(ddl_parts)


def build_generator_sft_data(valid_jsonl_path, split="train"):
    log_event("INFO", f"Building Generator SFT data from {valid_jsonl_path}")
    samples = load_jsonl(valid_jsonl_path)

    metadata_dir = Path(__file__).resolve().parent.parent / "data" / "processed" / "metadata"
    db_profiles = {}

    sft_rows = []

    for sample in samples:
        qid = sample["question_id"]
        db_id = sample["db_id"]
        question = sample["question"]
        evidence = sample.get("evidence", "")
        gold_sql = sample["SQL"]

        if db_id not in db_profiles:
            profile_path = metadata_dir / db_id / "column_profiles.json"
            if profile_path.exists():
                from common.io_utils import load_json
                db_profiles[db_id] = load_json(profile_path)
            else:
                db_profiles[db_id] = []

        profiles = db_profiles[db_id]
        if not profiles:
            continue

        ddl = get_mock_ddl(db_id, profiles)

        user_content = f"Question:\n{question}\n\nEvidence:\n{evidence or 'No evidence provided.'}\n\nSchema:\n{ddl}"

        sft_rows.append({
            "messages": [
                {
                    "role": "system",
                    "content": "You are a Text-to-SQL model. Generate valid SQLite SQL only."
                },
                {
                    "role": "user",
                    "content": user_content
                },
                {
                    "role": "assistant",
                    "content": gold_sql
                }
            ],
            "metadata": {
                "question_id": qid,
                "db_id": db_id
            }
        })

    output_path = Path(__file__).resolve().parent.parent / "data" / "processed" / "generator_sft" / f"generator_sft_{split}.jsonl"
    save_jsonl(sft_rows, str(output_path))
    log_event("INFO", f"Saved {len(sft_rows)} ChatML generator SFT samples to {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--valid_jsonl", default="data/processed/validation/valid_train.jsonl")
    parser.add_argument("--split", default="train")
    args = parser.parse_args()

    build_generator_sft_data(args.valid_jsonl, args.split)
