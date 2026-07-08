import json
import sqlite3
from pathlib import Path


def evaluate_execution_accuracy(predictions_path, gold_path, db_dir):
    """
    Evaluate Execution Accuracy (EX):
    predicted SQL and gold SQL must return the same result set.
    """
    predictions = json.load(open(predictions_path, "r", encoding="utf-8"))
    golds = json.load(open(gold_path, "r", encoding="utf-8"))

    gold_map = {g["question_id"]: g for g in golds}

    results = []
    correct = 0
    total = 0

    for pred in predictions:
        qid = pred["question_id"]
        db_id = pred["db_id"]
        gold = gold_map.get(qid)

        if not gold:
            results.append({
                "question_id": qid,
                "status": "missing_gold",
                "correct": False,
            })
            total += 1
            continue

        db_path = str(Path(db_dir) / db_id / f"{db_id}.sqlite")

        pred_result = safe_execute(db_path, pred["sql"])
        gold_result = safe_execute(db_path, gold["sql"])

        is_correct = compare_results(pred_result, gold_result)

        if is_correct:
            correct += 1

        total += 1
        results.append({
            "question_id": qid,
            "db_id": db_id,
            "predicted_sql": pred["sql"],
            "gold_sql": gold["sql"],
            "correct": is_correct,
            "pred_rows": len(pred_result) if pred_result is not None else None,
            "gold_rows": len(gold_result) if gold_result is not None else None,
        })

    accuracy = correct / total if total else 0.0

    summary = {
        "total": total,
        "correct": correct,
        "accuracy": accuracy,
        "details": results,
    }

    return summary


def safe_execute(db_path, sql, timeout=10):
    """
    Execute SQL query.
    NOTE: Direct execution of raw SQL strings carries a risk of SQL injection.
    This is intended and acceptable only for offline evaluation of gold-labeled datasets.
    """
    try:
        conn = sqlite3.connect(db_path, timeout=timeout)
        cursor = conn.execute(sql)
        rows = cursor.fetchall()
        conn.close()
        return rows
    except Exception:
        return None


def compare_results(pred_rows, gold_rows):
    if pred_rows is None or gold_rows is None:
        return False

    pred_set = set(tuple(r) for r in pred_rows)
    gold_set = set(tuple(r) for r in gold_rows)

    return pred_set == gold_set


def save_evaluation(summary, output_path):
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
