import json
from pathlib import Path
import sqlglot
from sqlglot import exp


def extract_sql_features(sql: str):
    try:
        tree = sqlglot.parse_one(sql)
    except Exception:
        return {"parse_error": True, "sql": sql}

    tables = sorted({t.name for t in tree.find_all(exp.Table)})
    columns = sorted({c.sql() for c in tree.find_all(exp.Column)})

    joins = []
    for join in tree.find_all(exp.Join):
        if join.args.get("on"):
            joins.append(join.args["on"].sql())

    where_clause = tree.args.get("where")
    group_clause = tree.args.get("group")

    return {
        "parse_error": False,
        "sql": sql,
        "tables": tables,
        "columns": columns,
        "joins": joins,
        "where": where_clause.sql() if where_clause else None,
        "group_by": group_clause.sql() if group_clause else None,
    }


def mine_logs(input_sql_json: str, output_path: str):
    with open(input_sql_json, "r", encoding="utf-8") as f:
        data = json.load(f)
    features = []

    for row in data:
        item = extract_sql_features(row["sql"])
        item["question_id"] = row.get("question_id")
        item["question"] = row.get("question")
        features.append(item)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(features, f, ensure_ascii=False, indent=2)
