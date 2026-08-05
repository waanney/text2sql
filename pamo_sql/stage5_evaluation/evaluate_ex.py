import json
import sqlite3
from pathlib import Path


def evaluate_execution_accuracy(predictions_path, gold_path, db_dir):
    """
    Evaluate Execution Accuracy (EX):
    predicted SQL and gold SQL must return the same result set.
    """
    predictions = json.load(open(predictions_path, "r", encoding="utf-8"))
    if isinstance(predictions, dict) and "results" in predictions:
        predictions = predictions["results"]
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

        pred_sql = pred.get("sql") or pred.get("predicted_sql")
        gold_sql = gold.get("sql") or gold.get("SQL")

        pred_result = safe_execute(db_path, pred_sql)
        gold_result = safe_execute(db_path, gold_sql)

        is_correct = compare_results(pred_result, gold_result)

        if is_correct:
            correct += 1

        total += 1
        results.append({
            "question_id": qid,
            "db_id": db_id,
            "predicted_sql": pred_sql,
            "gold_sql": gold_sql,
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
    if not sql:
        return None
    try:
        from common.sql_utils import clean_sql
        cleaned_sql = clean_sql(sql)
        conn = sqlite3.connect(db_path, timeout=timeout)
        cursor = conn.execute(cleaned_sql)
        rows = cursor.fetchall()
        conn.close()
        return rows
    except Exception:
        return None


def compare_results(pred_rows, gold_rows):
    if pred_rows is None or gold_rows is None:
        return False

    def normalize_val(val):
        if val is None:
            return None
        if isinstance(val, (int, float)):
            return round(float(val), 4)
        if isinstance(val, str):
            val_str = val.strip()
            try:
                return round(float(val_str), 4)
            except ValueError:
                return val_str
        return val

    def normalize_row(row):
        return tuple(normalize_val(v) for v in row)

    if len(pred_rows) != len(gold_rows):
        return False

    pred_norm = [normalize_row(r) for r in pred_rows]
    gold_norm = [normalize_row(r) for r in gold_rows]

    # Exact tuple set match
    if set(pred_norm) == set(gold_norm):
        return True

    # Column permutation match (if number of columns matches)
    if pred_norm and gold_norm and len(pred_norm[0]) == len(gold_norm[0]):
        import itertools
        num_cols = len(pred_norm[0])
        if num_cols <= 6:
            gold_set = set(gold_norm)
            for perm in itertools.permutations(range(num_cols)):
                permuted_pred = set(tuple(r[i] for i in perm) for r in pred_norm)
                if permuted_pred == gold_set:
                    return True

    return False


def save_evaluation(summary, output_path):
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Evaluate Execution Accuracy (EX) for BIRD dataset.")
    parser.add_argument("--predicted_out", default="artifacts/evaluation/evaluation_summary.json", help="Path to evaluation_summary.json predicted output.")
    parser.add_argument("--gold_path", default="pamo_sql/data/raw/bird/dev.json", help="Path to gold dataset JSON file.")
    parser.add_argument("--db_dir", default="pamo_sql/data/raw/bird/dev_databases", help="Directory containing BIRD databases.")
    parser.add_argument("--eval_output", default="artifacts/evaluation/execution_accuracy_results.json", help="Path to save evaluation results.")
    args = parser.parse_args()

    summary = evaluate_execution_accuracy(args.predicted_out, args.gold_path, args.db_dir)
    save_evaluation(summary, args.eval_output)
    
    print("\n================ EVALUATION SUMMARY ================")
    print(f"Total evaluated: {summary['total']}")
    print(f"Correct queries: {summary['correct']}")
    print(f"Execution Accuracy: {summary['accuracy'] * 100:.2f}%")
    print(f"Detailed results saved to: {args.eval_output}")
    print("====================================================\n")
