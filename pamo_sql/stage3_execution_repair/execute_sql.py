import sqlite3
import time


def execute_sql(db_path: str, sql: str, timeout_sec=10):
    start = time.time()

    try:
        conn = sqlite3.connect(db_path, timeout=timeout_sec)
        cursor = conn.execute(sql)
        rows = cursor.fetchall()
        columns = [d[0] for d in cursor.description] if cursor.description else []
        conn.close()

        return {
            "success": True,
            "error": None,
            "runtime_sec": time.time() - start,
            "row_count": len(rows),
            "column_count": len(columns),
            "columns": columns,
            "sample_rows": rows[:5],
            "is_empty": len(rows) == 0,
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "runtime_sec": time.time() - start,
            "row_count": None,
            "column_count": None,
            "columns": [],
            "sample_rows": [],
            "is_empty": None,
        }
