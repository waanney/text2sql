import json
from pathlib import Path
from collections import Counter


def analyze_errors(evaluation_path, predictions_path):
    """
    Analyze incorrect predictions to find error patterns.
    """
    evaluation = json.load(open(evaluation_path, "r", encoding="utf-8"))
    predictions = json.load(open(predictions_path, "r", encoding="utf-8"))

    pred_map = {p["question_id"]: p for p in predictions}
    errors = [d for d in evaluation.get("details", []) if not d.get("correct")]

    error_categories = Counter()
    error_details = []

    for err in errors:
        qid = err["question_id"]
        pred = pred_map.get(qid, {})

        category = classify_error(err, pred)
        error_categories[category] += 1

        error_details.append({
            "question_id": qid,
            "db_id": err.get("db_id"),
            "category": category,
            "predicted_sql": err.get("predicted_sql"),
            "gold_sql": err.get("gold_sql"),
            "source": pred.get("source"),
            "num_repairs": len(pred.get("repair_history", [])),
            "execution_success": pred.get("execution_metadata", {}).get("success"),
        })

    summary = {
        "total_errors": len(errors),
        "error_distribution": dict(error_categories.most_common()),
        "details": error_details,
    }

    return summary


def classify_error(err, pred):
    """Simple heuristic error classification."""
    exec_meta = pred.get("execution_metadata", {})

    if not exec_meta.get("success"):
        error_msg = exec_meta.get("error", "").lower()
        if "no such table" in error_msg:
            return "wrong_table"
        if "no such column" in error_msg:
            return "wrong_column"
        if "syntax" in error_msg:
            return "syntax_error"
        return "execution_error"

    if exec_meta.get("is_empty"):
        return "empty_result"

    pred_rows = err.get("pred_rows")
    gold_rows = err.get("gold_rows")
    if pred_rows is not None and gold_rows is not None:
        if pred_rows != gold_rows:
            return "wrong_row_count"

    return "wrong_values"


def save_error_analysis(summary, output_path):
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
