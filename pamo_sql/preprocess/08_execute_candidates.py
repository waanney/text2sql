import os
import sys
import sqlite3
import time
import argparse
from pathlib import Path

# Insert project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.io_utils import load_json, save_json, load_jsonl
from common.bird_utils import resolve_db_path
from common.result_compare import compare_results, hash_result, normalize_result
from common.logging_utils import log_event


def execute_candidates(valid_jsonl_path, split="train"):
    log_event("INFO", f"Executing candidates for split {split} from {valid_jsonl_path}")
    samples = load_jsonl(valid_jsonl_path)

    gold_exec_dir = Path(__file__).resolve().parent.parent / "data" / "cache" / "gold_execution" / split
    candidate_sql_dir = Path(__file__).resolve().parent.parent / "data" / "cache" / "candidate_sql" / split
    output_dir = Path(__file__).resolve().parent.parent / "data" / "cache" / "candidate_execution" / split
    output_dir.mkdir(parents=True, exist_ok=True)

    for sample in samples:
        qid = sample["question_id"]
        db_id = sample["db_id"]
        db_path = resolve_db_path(db_id)

        gold_exec_file = gold_exec_dir / f"{qid}.json"
        cand_sql_file = candidate_sql_dir / f"{qid}.json"

        if not gold_exec_file.exists() or not cand_sql_file.exists():
            continue

        gold_data = load_json(gold_exec_file)
        cand_data = load_json(cand_sql_file)

        # Get gold result for comparison
        gold_result = gold_data.get("result")
        gold_hash = gold_data.get("result_hash")

        executed_candidates = []

        for cand in cand_data.get("candidates", []):
            sql = cand["sql"]
            cid = cand["candidate_id"]
            source = cand["source"]

            start = time.time()
            conn = None
            try:
                conn = sqlite3.connect(db_path, timeout=5)
                cursor = conn.execute(sql)
                rows = cursor.fetchall()
                columns = [d[0] for d in cursor.description] if cursor.description else []
                runtime = time.time() - start

                res_normalized = normalize_result(rows)
                res_hash = hash_result(rows)
                
                # Check correctness
                is_correct = 1 if compare_results(rows, gold_result) else 0

                executed_candidates.append({
                    "candidate_id": cid,
                    "sql": sql,
                    "source": source,
                    "execution_success": True,
                    "error": None,
                    "runtime_sec": runtime,
                    "row_count": len(rows),
                    "column_count": len(columns),
                    "sample_rows": res_normalized[:5],
                    "result_hash": res_hash,
                    "is_correct": is_correct
                })

            except Exception as e:
                runtime = time.time() - start
                executed_candidates.append({
                    "candidate_id": cid,
                    "sql": sql,
                    "source": source,
                    "execution_success": False,
                    "error": str(e),
                    "runtime_sec": runtime,
                    "row_count": 0,
                    "column_count": 0,
                    "sample_rows": [],
                    "result_hash": None,
                    "is_correct": 0
                })
            finally:
                if conn:
                    conn.close()

        output = {
            "question_id": qid,
            "db_id": db_id,
            "gold_result_hash": gold_hash,
            "candidates": executed_candidates
        }

        save_json(output, str(output_dir / f"{qid}.json"))

    log_event("INFO", f"Finished candidate executions for split {split}.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--valid_jsonl", default="data/processed/validation/valid_train.jsonl")
    parser.add_argument("--split", default="train")
    args = parser.parse_args()

    execute_candidates(args.valid_jsonl, args.split)
