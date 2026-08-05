import os
import sys
import sqlite3
import time
import argparse
from pathlib import Path

# Insert project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.io_utils import load_jsonl, save_json, save_jsonl
from common.bird_utils import resolve_db_path
from common.result_compare import hash_result, normalize_result
from common.logging_utils import log_event


def execute_gold_sql(valid_jsonl_path, split="train"):
    log_event("INFO", f"Executing gold SQLs from {valid_jsonl_path}")
    samples = load_jsonl(valid_jsonl_path)

    cache_dir = Path(__file__).resolve().parent.parent / "data" / "cache" / "gold_execution" / split
    cache_dir.mkdir(parents=True, exist_ok=True)

    failed_samples = []

    for sample in samples:
        qid = sample["question_id"]
        db_id = sample["db_id"]
        sql = sample["SQL"]
        db_path = resolve_db_path(db_id)

        if not os.path.exists(db_path):
            log_event("ERROR", f"DB path {db_path} does not exist for sample {qid}")
            failed_samples.append({**sample, "error": "database missing"})
            continue

        start = time.time()
        conn = None
        try:
            conn = sqlite3.connect(db_path, timeout=10)
            cursor = conn.execute(sql)
            rows = cursor.fetchall()
            columns = [d[0] for d in cursor.description] if cursor.description else []
            runtime = time.time() - start

            res_normalized = normalize_result(rows)
            res_hash = hash_result(rows)

            output = {
                "question_id": qid,
                "db_id": db_id,
                "sql": sql,
                "success": True,
                "error": None,
                "runtime_sec": runtime,
                "columns": columns,
                "row_count": len(rows),
                "result": res_normalized,
                "result_hash": res_hash
            }

            save_json(output, str(cache_dir / f"{qid}.json"))

        except Exception as e:
            runtime = time.time() - start
            log_event("WARNING", f"Gold SQL failed for {qid}: {str(e)}")
            
            output = {
                "question_id": qid,
                "db_id": db_id,
                "sql": sql,
                "success": False,
                "error": str(e),
                "runtime_sec": runtime,
                "columns": [],
                "row_count": 0,
                "result": None,
                "result_hash": None
            }

            save_json(output, str(cache_dir / f"{qid}.json"))
            failed_samples.append({**sample, "error": str(e)})

        finally:
            if conn:
                conn.close()

    if failed_samples:
        suspicious_dir = Path(__file__).resolve().parent.parent / "data" / "processed" / "suspicious"
        suspicious_dir.mkdir(parents=True, exist_ok=True)
        save_jsonl(failed_samples, str(suspicious_dir / f"gold_sql_failed_{split}.jsonl"))
        log_event("WARNING", f"{len(failed_samples)} gold SQL executions failed. Saved to suspicious/gold_sql_failed_{split}.jsonl")
    else:
        log_event("INFO", f"All gold SQL executions succeeded for split {split}!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--valid_jsonl", default="data/processed/validation/valid_train.jsonl")
    parser.add_argument("--split", default="train")
    args = parser.parse_args()

    execute_gold_sql(args.valid_jsonl, args.split)
