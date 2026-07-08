import os
import sys
import argparse
import sqlglot
from pathlib import Path

# Insert project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.io_utils import load_json, save_jsonl
from common.bird_utils import resolve_db_path
from common.logging_utils import log_event


def validate_bird_file(input_path, split="train"):
    log_event("INFO", f"Validating BIRD file: {input_path}")
    raw_data = load_json(input_path)

    valid_samples = []
    invalid_samples = []

    for idx, sample in enumerate(raw_data):
        errors = []

        # Autogenerate question_id if not present
        if "question_id" not in sample:
            sample["question_id"] = f"{split}_{idx}"

        qid = sample["question_id"]

        if not sample.get("db_id"):
            errors.append("missing db_id")
        
        if not sample.get("question"):
            errors.append("missing question")

        if not sample.get("SQL"):
            errors.append("missing SQL")

        if "db_id" in sample:
            db_path = resolve_db_path(sample["db_id"])
            if not os.path.exists(db_path):
                errors.append(f"database file does not exist: {db_path}")

        # Basic parse validation
        if sample.get("SQL"):
            try:
                sqlglot.parse_one(sample["SQL"], read="sqlite")
            except Exception as e:
                errors.append(f"SQL parsing failed: {str(e)}")

        if errors:
            sample["errors"] = errors
            invalid_samples.append(sample)
            log_event("WARNING", f"Sample {qid} is invalid: {errors}")
        else:
            valid_samples.append(sample)

    processed_dir = Path(__file__).resolve().parent.parent / "data" / "processed" / "validation"
    valid_out = processed_dir / f"valid_{split}.jsonl"
    invalid_out = processed_dir / f"invalid_{split}.jsonl"

    save_jsonl(valid_samples, str(valid_out))
    save_jsonl(invalid_samples, str(invalid_out))

    log_event("INFO", f"Validation finished for split {split}. Valid: {len(valid_samples)}, Invalid: {len(invalid_samples)}")
    return str(valid_out), str(invalid_out)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/raw/bird/train.json")
    parser.add_argument("--split", default="train")
    args = parser.parse_args()

    validate_bird_file(args.input, args.split)
