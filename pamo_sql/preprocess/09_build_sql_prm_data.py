import os
import sys
import argparse
import itertools
import random
from pathlib import Path

# Insert project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.io_utils import load_json, save_jsonl, load_jsonl
from common.logging_utils import log_event


def score_candidate(cand):
    """
    Assign a relative quality score to a candidate.
    Higher is better.
    """
    is_correct = cand.get("is_correct", 0)
    exec_success = cand.get("execution_success", False)
    row_count = cand.get("row_count", 0)
    runtime = cand.get("runtime_sec", 999.0)
    
    if is_correct:
        # Correct candidates: prioritize faster execution
        speed_bonus = max(0.0, min(1.0, 1.0 - (runtime / 10.0)))
        return 2.0 + speed_bonus
    
    if exec_success:
        # Executable but wrong: prefer non-empty over empty
        if row_count > 0:
            return 1.5
        return 1.0
        
    return 0.0


def build_sql_prm_data(valid_jsonl_path, split="train"):
    log_event("INFO", f"Building SQL-PRM selector dataset from {valid_jsonl_path}")
    samples = load_jsonl(valid_jsonl_path)

    cand_exec_dir = Path(__file__).resolve().parent.parent / "data" / "cache" / "candidate_execution" / split
    metadata_dir = Path(__file__).resolve().parent.parent / "data" / "processed" / "metadata"

    listwise_rows = []
    pairwise_rows = []

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

        # 1. Build Listwise selector data
        correct_cands = [c for c in candidates if c.get("is_correct") == 1]
        best_cand_id = None
        if correct_cands:
            # Pick fastest correct candidate
            best_cand = min(correct_cands, key=lambda x: x.get("runtime_sec", 999.0))
            best_cand_id = best_cand["candidate_id"]

        listwise_rows.append({
            "question_id": qid,
            "db_id": db_id,
            "question": question,
            "evidence": evidence,
            "candidates": candidates,
            "best_candidate_id": best_cand_id
        })

        # 2. Build Pairwise selector data
        scored_candidates = []
        for c in candidates:
            scored_candidates.append((c, score_candidate(c)))

        pairs = list(itertools.combinations(scored_candidates, 2))
        # Sample a subset of pairs to prevent explosion (max 20 per question)
        if len(pairs) > 20:
            pairs = random.sample(pairs, 20)

        for (c_a, score_a), (c_b, score_b) in pairs:
            if score_a == score_b:
                winner = "tie"
            elif score_a > score_b:
                winner = "A"
            else:
                winner = "B"

            prompt = f"""Question:
{question}

Evidence:
{evidence}

SQL A:
{c_a['sql']}
Execution A:
success={c_a['execution_success']}, rows={c_a['row_count']}, error={c_a['error']}

SQL B:
{c_b['sql']}
Execution B:
success={c_b['execution_success']}, rows={c_b['row_count']}, error={c_b['error']}

Which SQL is better? Answer A, B, or tie."""

            pairwise_rows.append({
                "question_id": qid,
                "db_id": db_id,
                "prompt": prompt,
                "chosen": "A" if winner == "A" else ("B" if winner == "B" else "tie"),
                "rejected": "B" if winner == "A" else ("A" if winner == "B" else "tie"),
                "winner": winner,
                "candidate_a": c_a,
                "candidate_b": c_b
            })

    # Save outputs
    out_dir = Path(__file__).resolve().parent.parent / "data" / "processed" / "sql_prm_selector"
    out_dir.mkdir(parents=True, exist_ok=True)

    save_jsonl(listwise_rows, str(out_dir / f"listwise_selector_{split}.jsonl"))
    save_jsonl(pairwise_rows, str(out_dir / f"pairwise_selector_{split}.jsonl"))

    log_event("INFO", f"Saved {len(listwise_rows)} listwise rows and {len(pairwise_rows)} pairwise rows for split {split}.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--valid_jsonl", default="data/processed/validation/valid_train.jsonl")
    parser.add_argument("--split", default="train")
    args = parser.parse_args()

    build_sql_prm_data(args.valid_jsonl, args.split)
