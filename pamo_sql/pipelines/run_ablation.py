import os
import sys
import yaml
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
from pipelines.run_dataset import load_schema_and_profiles
from common.result_compare import compare_results
import sqlite3


def get_ablation_config(base_config, overrides):
    """Deep merge overrides into base config."""
    config = json.loads(json.dumps(base_config))  # deep copy
    
    for key, value in overrides.items():
        parts = key.split(".")
        curr = config
        for p in parts[:-1]:
            if p not in curr:
                curr[p] = {}
            curr = curr[p]
        curr[parts[-1]] = value
        
    return config


def execute_sql_safely(db_path, sql):
    if not sql or not os.path.exists(db_path):
        return None
    try:
        conn = sqlite3.connect(db_path, timeout=5)
        res = conn.execute(sql).fetchall()
        conn.close()
        return res
    except Exception:
        return None


def run_ablation(ablation_yaml_path, dataset_json_path, raw_bird_dir, output_dir, limit=5):
    log_event("INFO", f"Loading ablation configuration from {ablation_yaml_path}")
    with open(ablation_yaml_path, "r", encoding="utf-8") as f:
        ablation_meta = yaml.safe_load(f)

    with open(dataset_json_path, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    if limit:
        dataset = dataset[:limit]

    base_config = {
        "stages": ablation_meta.get("stages", {}),
        "generation": ablation_meta.get("generation", {}),
        "selector": ablation_meta.get("selector", {})
    }

    results_summary = {}

    for variant in ablation_meta.get("ablation_variants", []):
        name = variant["name"]
        overrides = variant.get("overrides", {})
        log_event("INFO", f"=== Running Ablation Variant: {name} ===")

        v_config = get_ablation_config(base_config, overrides)

        # Instantiate selector based on method
        method = v_config.get("selector", {}).get("method", "llm_pairwise")
        if method == "trained_prm":
            prm_path = str(pamo_sql_dir / "artifacts" / "models" / "sql_prm_selector")
            if os.path.exists(prm_path):
                selector = SQLPRMSelector(prm_path)
            else:
                log_event("WARNING", f"PRM path {prm_path} not found. Falling back to LLMPairwiseSelector.")
                selector = LLMPairwiseSelector()
        else:
            selector = LLMPairwiseSelector()

        correct_count = 0
        total_count = 0
        predictions = []

        for idx, sample in enumerate(dataset):
            qid = sample.get("question_id", f"sample_{idx}")
            db_id = sample["db_id"]
            db_path = str(Path(raw_bird_dir) / "database" / db_id / f"{db_id}.sqlite")

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
                    config=v_config,
                    artifacts_dir=str(Path(output_dir) / name)
                )

                pred_sql = selection.get("final_sql", "")
                gold_sql = sample.get("SQL", "")

                # Compare execution results
                pred_res = execute_sql_safely(db_path, pred_sql)
                gold_res = execute_sql_safely(db_path, gold_sql)

                is_correct = compare_results(pred_res, gold_res)
                if is_correct:
                    correct_count += 1
                
                total_count += 1

                predictions.append({
                    "question_id": qid,
                    "predicted_sql": pred_sql,
                    "gold_sql": gold_sql,
                    "is_correct": int(is_correct)
                })

            except Exception as e:
                log_event("ERROR", f"Error in variant {name} for sample {qid}: {str(e)}")
                total_count += 1
                predictions.append({
                    "question_id": qid,
                    "predicted_sql": "",
                    "gold_sql": sample.get("SQL", ""),
                    "is_correct": 0,
                    "error": str(e)
                })

        accuracy = correct_count / total_count if total_count else 0.0
        log_event("INFO", f"Variant {name} accuracy: {accuracy:.4f} ({correct_count}/{total_count})")

        results_summary[name] = {
            "accuracy": accuracy,
            "correct": correct_count,
            "total": total_count,
            "predictions": predictions
        }

    # Save summary report
    report_path = Path(output_dir) / "ablation_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(results_summary, f, ensure_ascii=False, indent=2)

    log_event("INFO", f"Ablation study complete. Report saved to {report_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ablation_yaml", default="configs/experiment_ablation.yaml")
    parser.add_argument("--dataset", default="data/raw/bird/dev.json")
    parser.add_argument("--bird_dir", default="data/raw/bird")
    parser.add_argument("--output_dir", default="artifacts/ablation")
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args()

    run_ablation(
        ablation_yaml_path=args.ablation_yaml,
        dataset_json_path=args.dataset,
        raw_bird_dir=args.bird_dir,
        output_dir=args.output_dir,
        limit=args.limit
    )
