import json
import time
from pathlib import Path


def evaluate_latency(predictions_path, pipeline_logs_path=None):
    """
    Evaluate per-question latency from pipeline logs or re-measure.
    """
    predictions = json.load(open(predictions_path, "r", encoding="utf-8"))

    results = []
    total_time = 0.0

    for pred in predictions:
        gen_meta = pred.get("generation_metadata", {})
        exec_meta = pred.get("execution_metadata", {})

        gen_time = gen_meta.get("generation_time_sec", 0)
        exec_time = exec_meta.get("runtime_sec", 0)
        repair_time = sum(
            r.get("repair_time_sec", 0)
            for r in pred.get("repair_history", [])
        )

        total_question_time = gen_time + exec_time + repair_time
        total_time += total_question_time

        results.append({
            "question_id": pred["question_id"],
            "generation_time_sec": gen_time,
            "execution_time_sec": exec_time,
            "repair_time_sec": repair_time,
            "total_time_sec": total_question_time,
        })

    n = len(results)
    avg_time = total_time / n if n else 0

    summary = {
        "total_questions": n,
        "total_time_sec": total_time,
        "avg_time_per_question_sec": avg_time,
        "max_time_sec": max((r["total_time_sec"] for r in results), default=0),
        "min_time_sec": min((r["total_time_sec"] for r in results), default=0),
        "details": results,
    }

    return summary
