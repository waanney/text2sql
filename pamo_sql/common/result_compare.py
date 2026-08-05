import hashlib
import json
from common.execution_utils import normalize_result as norm_res

def normalize_result(rows):
    return norm_res(rows)

def compare_results(pred_rows, gold_rows):
    if pred_rows is None or gold_rows is None:
        return False
    try:
        norm_pred = normalize_result(pred_rows)
        norm_gold = normalize_result(gold_rows)
        return norm_pred == norm_gold
    except Exception:
        return False

def hash_result(rows):
    if rows is None:
        return None
    try:
        norm = normalize_result(rows)
        serialized = json.dumps(norm, sort_keys=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    except Exception:
        return None
