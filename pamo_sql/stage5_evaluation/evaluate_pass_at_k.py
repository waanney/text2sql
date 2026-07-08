"""
Evaluate Pass@k and oracle candidate accuracy.
This tells us if the issue is in generation or selection.
"""

import json
import sqlite3
from pathlib import Path


def evaluate_pass_at_k(candidates_dir, gold_path, db_dir, k_values=None):
    """
    For each question, check if at least one of the top-k candidates is correct.

    Pass@k measures generator quality independent of selector.
    """
    if k_values is None:
        k_values = [1, 3, 5, 10]

    with open(gold_path, "r", encoding="utf-8") as f:
        golds = json.load(f)
    gold_map = {g["question_id"]: g for g in golds}

    results_per_k = {k: {"correct": 0, "total": 0} for k in k_values}
    oracle_correct = 0
    total = 0
    details = []

    candidates_path = Path(candidates_dir)
    for cand_file in sorted(candidates_path.glob("*_repaired.json")):
        with open(cand_file, "r", encoding="utf-8") as f:
            candidates = json.load(f)

        if not candidates:
            continue

        qid = candidates[0].get("question_id")
        db_id = candidates[0].get("db_id")
        gold = gold_map.get(qid)
        if not gold:
            continue

        db_path = str(Path(db_dir) / db_id / f"{db_id}.sqlite")

        # Execute gold SQL
        gold_result = safe_execute(db_path, gold["sql"])
        if gold_result is None:
            continue

        total += 1
        gold_set = set(tuple(r) for r in gold_result)

        # Check each candidate
        candidate_correctness = []
        for c in candidates:
            ex = c.get("execution_metadata", {})
            if not ex.get("success"):
                candidate_correctness.append(False)
                continue

            pred_result = safe_execute(db_path, c["sql"])
            if pred_result is None:
                candidate_correctness.append(False)
                continue

            pred_set = set(tuple(r) for r in pred_result)
            candidate_correctness.append(pred_set == gold_set)

        # Oracle: any candidate correct?
        any_correct = any(candidate_correctness)
        if any_correct:
            oracle_correct += 1

        # Pass@k
        for k in k_values:
            results_per_k[k]["total"] += 1
            if any(candidate_correctness[:k]):
                results_per_k[k]["correct"] += 1

        details.append({
            "question_id": qid,
            "db_id": db_id,
            "num_candidates": len(candidates),
            "num_correct": sum(candidate_correctness),
            "oracle_correct": any_correct,
            "correctness_by_position": candidate_correctness,
        })

    summary = {
        "total_questions": total,
        "oracle_accuracy": oracle_correct / total if total else 0,
        "oracle_correct": oracle_correct,
    }

    for k in k_values:
        r = results_per_k[k]
        summary[f"pass_at_{k}"] = r["correct"] / r["total"] if r["total"] else 0

    summary["details"] = details

    return summary


def safe_execute(db_path, sql, timeout=10):
    try:
        conn = sqlite3.connect(db_path, timeout=timeout)
        cursor = conn.execute(sql)
        rows = cursor.fetchall()
        conn.close()
        return rows
    except Exception:
        return None
