import sqlite3
import json
from pathlib import Path


def list_tables(conn):
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table';"
    ).fetchall()
    return [r[0] for r in rows]


def list_columns(conn, table):
    rows = conn.execute(f"PRAGMA table_info('{table}')").fetchall()
    return [{"name": r[1], "type": r[2]} for r in rows]


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

    return {
        "table_name": table,
        "column_name": column,
        "total_rows": total,
        "null_ratio": nulls / total if total else 0,
        "distinct_count": distinct_count,
        "top_values": [{"value": str(v), "count": c} for v, c in top_values],
        "min_value": str(min_value) if min_value is not None else None,
        "max_value": str(max_value) if max_value is not None else None,
    }


def profile_database(db_path: str, output_path: str):
    conn = sqlite3.connect(db_path)
    profiles = []

    for table in list_tables(conn):
        for col in list_columns(conn, table):
            p = profile_column(conn, table, col["name"])
            p["data_type"] = col["type"]
            profiles.append(p)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(profiles, f, ensure_ascii=False, indent=2)

    conn.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Profile SQLite Database columns.")
    parser.add_argument(
        "--db_path",
        default="data/raw/databases/california_schools.sqlite",
        help="Path to SQLite database file"
    )
    parser.add_argument(
        "--output_path",
        default="artifacts/metadata/california_schools/profile.json",
        help="Path to save profiled metadata JSON"
    )
    args = parser.parse_args()

    profile_database(db_path=args.db_path, output_path=args.output_path)
