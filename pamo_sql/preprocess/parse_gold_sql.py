import os
import sys
import argparse
import sqlglot
import sqlglot.expressions as exp
from pathlib import Path

# Insert project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.io_utils import load_jsonl, save_json, save_jsonl
from common.logging_utils import log_event


def parse_sql_to_features(sql):
    parsed = sqlglot.parse_one(sql, read="sqlite")
    
    try:
        qualified = sqlglot.optimizer.qualify.qualify(parsed)
    except Exception:
        qualified = parsed
        
    tables_used = set()
    columns_used = set()
    selected_columns = set()
    where_columns = set()
    join_predicates = []
    group_by_columns = set()
    order_by_columns = set()
    aggregation_functions = []
    literals_used = []

    for table in qualified.find_all(exp.Table):
        tables_used.add(table.name)

    for column in qualified.find_all(exp.Column):
        col_name = f"{column.text('table')}.{column.name}" if column.text('table') else column.name
        columns_used.add(col_name)

        parent = column.parent
        while parent:
            if isinstance(parent, exp.Select):
                if any(column in expr for expr in parent.expressions):
                    selected_columns.add(col_name)
                break
            elif isinstance(parent, exp.Where):
                where_columns.add(col_name)
                break
            elif isinstance(parent, exp.Group):
                group_by_columns.add(col_name)
                break
            elif isinstance(parent, exp.Order):
                order_by_columns.add(col_name)
                break
            parent = parent.parent

    for join in qualified.find_all(exp.Join):
        on_clause = join.args.get("on")
        if on_clause:
            join_predicates.append(str(on_clause))

    # Basic functions
    for func in qualified.find_all(exp.Func):
        if func.sql_name() in ("SUM", "COUNT", "AVG", "MIN", "MAX"):
            aggregation_functions.append(func.sql_name())

    for lit in qualified.find_all(exp.Literal):
        literals_used.append(lit.name)

    return {
        "tables_used": sorted(list(tables_used)),
        "columns_used": sorted(list(columns_used)),
        "selected_columns": sorted(list(selected_columns)),
        "where_columns": sorted(list(where_columns)),
        "join_predicates": join_predicates,
        "group_by_columns": sorted(list(group_by_columns)),
        "order_by_columns": sorted(list(order_by_columns)),
        "aggregation_functions": aggregation_functions,
        "literals_used": literals_used
    }


def parse_gold_sqls(valid_jsonl_path, split="train"):
    log_event("INFO", f"Parsing gold SQLs from {valid_jsonl_path}")
    samples = load_jsonl(valid_jsonl_path)

    cache_dir = Path(__file__).resolve().parent.parent / "data" / "cache" / "parsed_sql" / split
    cache_dir.mkdir(parents=True, exist_ok=True)

    failed_samples = []

    for sample in samples:
        qid = sample["question_id"]
        sql = sample["SQL"]

        try:
            features = parse_sql_to_features(sql)
            output = {
                "question_id": qid,
                "db_id": sample["db_id"],
                **features
            }
            save_json(output, str(cache_dir / f"{qid}.json"))

        except Exception as e:
            log_event("WARNING", f"Failed parsing SQL for {qid}: {str(e)}")
            failed_samples.append({**sample, "error": str(e)})

    if failed_samples:
        suspicious_dir = Path(__file__).resolve().parent.parent / "data" / "processed" / "suspicious"
        suspicious_dir.mkdir(parents=True, exist_ok=True)
        save_jsonl(failed_samples, str(suspicious_dir / f"parse_failed_{split}.jsonl"))
        log_event("WARNING", f"{len(failed_samples)} SQL parses failed. Saved to suspicious/parse_failed_{split}.jsonl")
    else:
        log_event("INFO", f"All SQL parses succeeded for split {split}!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--valid_jsonl", default="data/processed/validation/valid_train.jsonl")
    parser.add_argument("--split", default="train")
    args = parser.parse_args()

    parse_gold_sqls(args.valid_jsonl, args.split)
