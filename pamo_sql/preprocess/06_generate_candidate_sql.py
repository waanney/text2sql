import os
import sys
import argparse
from pathlib import Path

# Insert project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.io_utils import load_jsonl, save_json
from preprocess.07_mutate_gold_sql import mutate_sql
from common.logging_utils import log_event


def generate_candidate_sqls(valid_jsonl_path, split="train"):
    log_event("INFO", f"Generating candidate SQLs from {valid_jsonl_path}")
    samples = load_jsonl(valid_jsonl_path)

    cache_dir = Path(__file__).resolve().parent.parent / "data" / "cache" / "candidate_sql" / split
    cache_dir.mkdir(parents=True, exist_ok=True)

    for sample in samples:
        qid = sample["question_id"]
        db_id = sample["db_id"]
        gold_sql = sample["SQL"]

        candidates = []

        # 1. Gold candidate
        candidates.append({
            "candidate_id": f"{qid}_gold",
            "source": "gold",
            "sql": gold_sql
        })

        # 2. Mutated candidates (hard negatives)
        mutations = mutate_sql(gold_sql)
        for mut_type, mut_sql in mutations.items():
            candidates.append({
                "candidate_id": f"{qid}_mut_{mut_type}",
                "source": f"mutation_{mut_type}",
                "sql": mut_sql
            })

        # 3. Simulate minor generator candidates (slight syntax variations)
        candidates.append({
            "candidate_id": f"{qid}_gen_reasoning_0",
            "source": "reasoning_generator",
            "sql": gold_sql.replace("SELECT", "select")
        })

        if "join" in gold_sql.lower():
            # simulate a join generator that missed one join
            candidates.append({
                "candidate_id": f"{qid}_gen_join_0",
                "source": "join_focused_generator",
                "sql": gold_sql.split("JOIN")[0]  # incomplete join query
            })

        output = {
            "question_id": qid,
            "db_id": db_id,
            "candidates": candidates
        }

        save_json(output, str(cache_dir / f"{qid}.json"))

    log_event("INFO", f"Finished generating candidate pools for split {split}.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--valid_jsonl", default="data/processed/validation/valid_train.jsonl")
    parser.add_argument("--split", default="train")
    args = parser.parse_args()

    generate_candidate_sqls(args.valid_jsonl, args.split)
