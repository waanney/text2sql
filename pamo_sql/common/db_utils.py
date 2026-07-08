import sqlite3
from typing import List, Dict, Any, Tuple


def get_db_connection(db_path: str, timeout: float = 10.0) -> sqlite3.Connection:
    """Establish connection to SQLite database."""
    conn = sqlite3.connect(db_path, timeout=timeout)
    # Enable foreign keys and row factory for ease of access
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def execute_query(db_path: str, sql: str, timeout: float = 5.0) -> Tuple[bool, Any]:
    """Execute SQL query safely and return success status and rows/error."""
    try:
        with get_db_connection(db_path, timeout=timeout) as conn:
            cursor = conn.execute(sql)
            rows = cursor.fetchall()
            return True, rows
    except Exception as e:
        return False, str(e)


def get_tables(db_path: str) -> List[str]:
    """Get list of all user table names in the database."""
    try:
        with get_db_connection(db_path) as conn:
            rows = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';"
            ).fetchall()
            return [r[0] for r in rows]
    except Exception:
        return []


def get_columns_metadata(db_path: str, table_name: str) -> List[Dict[str, Any]]:
    """Retrieve metadata (name, type, nullability, primary key) for a table's columns."""
    try:
        with get_db_connection(db_path) as conn:
            rows = conn.execute(f"PRAGMA table_info('{table_name}')").fetchall()
            # PRAGMA table_info returns: (cid, name, type, notnull, dflt_value, pk)
            return [
                {
                    "name": r[1],
                    "type": r[2],
                    "notnull": bool(r[3]),
                    "primary_key": bool(r[5])
                }
                for r in rows
            ]
    except Exception:
        return []


def check_value_exists(db_path: str, table: str, column: str, value: str) -> bool:
    """Check if a specific string literal value exists in a table's column."""
    sql = f'SELECT 1 FROM "{table}" WHERE "{column}" = ? LIMIT 1'
    try:
        with get_db_connection(db_path) as conn:
            res = conn.execute(sql, (value,)).fetchone()
            return res is not None
    except Exception:
        return False
