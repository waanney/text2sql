import os
import sys
import json
import argparse
import time
from pathlib import Path

# Setup sys.path to allow imports from pamo_sql root
pamo_sql_dir = Path(__file__).resolve().parent.parent
if str(pamo_sql_dir) not in sys.path:
    sys.path.insert(0, str(pamo_sql_dir))

from pipelines.run_single_question import run_single_question
from stage4_sql_prm_selection.llm_tie_breaker import LLMPairwiseSelector
from stage4_sql_prm_selection.infer_sql_prm import SQLPRMSelector
from common.logging_utils import log_event


from common.schema_utils import get_rich_schema_ddl, extract_value_links


def load_schema_and_profiles(db_id, raw_bird_dir):
    """
    Rich schema & profile loader with representative column data samples.
    """
    db_path = Path(raw_bird_dir) / "database" / db_id / f"{db_id}.sqlite"
    
    # Heuristically check processed metadata
    metadata_dir = pamo_sql_dir / "data" / "processed" / "metadata" / db_id
    profile_path = metadata_dir / "column_profiles.json"
    
    if profile_path.exists():
        with open(profile_path, "r", encoding="utf-8") as f:
            profiles = json.load(f)
    else:
        profiles = []

    # Get enriched DDL schema with 3 sample values per column
    ddl_schema = get_rich_schema_ddl(str(db_path))
    if not ddl_schema and db_path.exists():
        import sqlite3
        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            rows = cursor.execute("SELECT sql FROM sqlite_master WHERE type='table'").fetchall()
            ddl_schema = "\n".join([r[0] for r in rows if r[0]])
            conn.close()
        except Exception:
            pass

    return profiles, ddl_schema, ddl_schema


def run_dataset(dataset_json_path, raw_bird_dir, output_dir, limit=None, selector_type="llm", prm_path=None):
    log_event("INFO", f"Running dataset evaluation on {dataset_json_path}")
    
    with open(dataset_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if limit:
        data = data[:limit]

    # Initialize Selector
    if selector_type == "prm" and prm_path:
        log_event("INFO", f"Using Trained SQL-PRM Selector from {prm_path}")
        selector = SQLPRMSelector(prm_path)
    else:
        log_event("INFO", "Using LLM Pairwise Selector")
        selector = LLMPairwiseSelector()

    results = []
    start_time = time.time()

    for idx, sample in enumerate(data):
        qid = sample.get("question_id", f"sample_{idx}")
        db_id = sample["db_id"]
        db_path = str(Path(raw_bird_dir) / "database" / db_id / f"{db_id}.sqlite")

        log_event("INFO", f"Processing {idx+1}/{len(data)}: Question ID {qid}")

        profiles, ddl, light_schema = load_schema_and_profiles(db_id, raw_bird_dir)

        try:
            selection = run_single_question(
                question_input={
                    "question_id": qid,
                    "question": sample["question"],
                    "db_id": db_id,
                    "evidence": sample.get("evidence", "")
                },
                db_path=db_path,
                column_summaries=profiles,
                ddl_schema=ddl,
                light_schema=light_schema,
                selector=selector,
                artifacts_dir=output_dir
            )

            # Record result
            results.append({
                "question_id": qid,
                "db_id": db_id,
                "question": sample["question"],
                "gold_sql": sample.get("SQL", ""),
                "predicted_sql": selection.get("final_sql", ""),
                "hard_case": selection.get("hard_case", False),
                "num_original_candidates": selection.get("num_original_candidates", 0)
            })

        except Exception as e:
            log_event("ERROR", f"Failed executing pipeline for {qid}: {str(e)}")
            results.append({
                "question_id": qid,
                "db_id": db_id,
                "question": sample["question"],
                "gold_sql": sample.get("SQL", ""),
                "predicted_sql": "",
                "error": str(e)
            })

    # Save summary
    duration = time.time() - start_time
    summary_path = Path(output_dir) / "evaluation_summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)

    summary = {
        "dataset": dataset_json_path,
        "selector_type": selector_type,
        "total_samples": len(data),
        "evaluated_samples": len(results),
        "duration_sec": duration,
        "results": results
    }

    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    log_event("INFO", f"Evaluation finished. Summary saved to {summary_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="pamo_sql/data/raw/bird/dev.json")
    parser.add_argument("--bird_dir", default="pamo_sql/data/raw/bird")
    parser.add_argument("--output_dir", default="artifacts/evaluation")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--selector", default="llm", choices=["llm", "prm"])
    parser.add_argument("--prm_path", default="artifacts/models/sql_prm_selector")
    args = parser.parse_args()

    run_dataset(
        dataset_json_path=args.dataset,
        raw_bird_dir=args.bird_dir,
        output_dir=args.output_dir,
        limit=args.limit,
        selector_type=args.selector,
        prm_path=args.prm_path
    )
