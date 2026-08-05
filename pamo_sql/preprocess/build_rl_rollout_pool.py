import os
import sys
import argparse
from pathlib import Path

# Insert project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.io_utils import load_json, save_jsonl, load_jsonl
from common.logging_utils import log_event


def compute_reward(cand):
    is_correct = cand.get("is_correct", 0)
    exec_success = cand.get("execution_success", False)
    
    if is_correct:
        return 1.0
    elif not exec_success:
        return 0.0
    else:
        # Executable but incorrect: small auxiliary reward
        return 0.2


def build_rl_rollout_pool(valid_jsonl_path, split="train"):
    log_event("INFO", f"Building RL rollout pool for split {split} from {valid_jsonl_path}")
    samples = load_jsonl(valid_jsonl_path)

    cand_exec_dir = Path(__file__).resolve().parent.parent / "data" / "cache" / "candidate_execution" / split
    dataset_rows = []

    for sample in samples:
        qid = sample["question_id"]
        db_id = sample["db_id"]
        question = sample["question"]
        evidence = sample.get("evidence", "")

        cand_exec_file = cand_exec_dir / f"{qid}.json"
        if not cand_exec_file.exists():
            continue

        cand_data = load_json(cand_exec_file)
        candidates = cand_data.get("candidates", [])

        if not candidates:
            continue

        reward_map = {}
        for c in candidates:
            reward_map[c["candidate_id"]] = compute_reward(c)

        prompt = f"Question: {question}\nEvidence: {evidence or 'None'}\nChoose the best candidate SQL ID from below."

        dataset_rows.append({
            "question_id": qid,
            "db_id": db_id,
            "prompt": prompt,
            "candidates": candidates,
            "reward_map": reward_map
        })

    output_path = Path(__file__).resolve().parent.parent / "data" / "processed" / "rl_selector" / f"rl_rollout_pool_{split}.jsonl"
    save_jsonl(dataset_rows, str(output_path))
    log_event("INFO", f"Saved {len(dataset_rows)} RL rollout pool items to {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--valid_jsonl", default="data/processed/validation/valid_train.jsonl")
    parser.add_argument("--split", default="train")
    args = parser.parse_args()

    build_rl_rollout_pool(args.valid_jsonl, args.split)
