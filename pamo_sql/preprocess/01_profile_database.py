import os
import sys
import sqlite3
import argparse
import re
from pathlib import Path

# Insert project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.io_utils import save_json
from common.bird_utils import resolve_db_path
from common.logging_utils import log_event


def list_tables(conn):
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table';"
    ).fetchall()
    return [r[0] for r in rows]


def list_columns(conn, table):
    rows = conn.execute(f"PRAGMA table_info('{table}')").fetchall()
    return [{"name": r[1], "type": r[2]} for r in rows]


def detect_value_shape(values):
    if not values:
        return "text_phrase"
    
    numeric_count = 0
    date_count = 0
    boolean_count = 0
    code_count = 0
    
    for val in values:
        val_str = str(val).strip().lower()
        if not val_str:
            continue
        
        try:
            float(val_str)
            numeric_count += 1
            continue
        except ValueError:
            pass
        
        if re.match(r'^\d{4}[-/]\d{1,2}[-/]\d{1,2}$', val_str) or re.match(r'^\d{1,2}[-/]\d{1,2}[-/]\d{2,4}$', val_str):
            date_count += 1
            continue
            
        if val_str in ("y", "n", "yes", "no", "true", "false", "1", "0", "t", "f"):
            boolean_count += 1
            continue
            
        if len(val_str) <= 6:
            code_count += 1
            continue

    total = len(values)
    if numeric_count / total > 0.8:
        return "numeric"
    if date_count / total > 0.8:
        return "date"
    if boolean_count / total > 0.8:
        return "boolean"
    if code_count / total > 0.8:
        return "code"
    return "text_phrase"


def profile_column(conn, table, column, limit_top_values=20):
    quoted_table = f'"{table}"'
    quoted_col = f'"{column}"'

    total = conn.execute(f"SELECT COUNT(*) FROM {quoted_table}").fetchone()[0]
    nulls = conn.execute(
        f"SELECT COUNT(*) FROM {quoted_table} WHERE {quoted_col} IS NULL"
    ).fetchone()[0]
    distinct_count = conn.execute(
        f"SELECT COUNT(DISTINCT {quoted_col}) FROM {quoted_table}"
    ).fetchone()[0]

    top_values = conn.execute(
        f"""
        SELECT {quoted_col}, COUNT(*) as cnt
        FROM {quoted_table}
        WHERE {quoted_col} IS NOT NULL
        GROUP BY {quoted_col}
        ORDER BY cnt DESC
        LIMIT {limit_top_values}
        """
    ).fetchall()

    try:
        min_value, max_value = conn.execute(
            f"SELECT MIN({quoted_col}), MAX({quoted_col}) FROM {quoted_table}"
        ).fetchone()
    except Exception:
        min_value, max_value = None, None

    sample_values = [v[0] for v in top_values if v[0] is not None]
    value_shape = detect_value_shape(sample_values)

    return {
        "table_name": table,
        "column_name": column,
        "total_rows": total,
        "null_count": nulls,
        "null_ratio": nulls / total if total else 0,
        "distinct_count": distinct_count,
        "top_k_values": [{"value": str(v), "count": c} for v, c in top_values],
        "min_value": str(min_value) if min_value is not None else None,
        "max_value": str(max_value) if max_value is not None else None,
        "value_shape": value_shape,
        "example_values": [str(v) for v in sample_values[:5]]
    }


def profile_database_by_id(db_id: str, output_path: str):
    db_path = resolve_db_path(db_id)
    if not os.path.exists(db_path):
        log_event("ERROR", f"Database {db_id} not found at {db_path}")
        return

    log_event("INFO", f"Profiling database: {db_id} ({db_path})")
    conn = sqlite3.connect(db_path)
    profiles = []

    for table in list_tables(conn):
        for col in list_columns(conn, table):
            try:
                p = profile_column(conn, table, col["name"])
                p["declared_type"] = col["type"]
                p["db_id"] = db_id
                profiles.append(p)
            except Exception as e:
                log_event("ERROR", f"Failed profiling column {table}.{col['name']}: {str(e)}")

    save_json(profiles, output_path)
    conn.close()
    log_event("INFO", f"Saved {len(profiles)} column profiles to {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--db_id", default="california_schools")
    parser.add_argument("--output", default="data/processed/metadata/california_schools/column_profiles.json")
    args = parser.parse_args()

    profile_database_by_id(args.db_id, args.output)
