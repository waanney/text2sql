import sqlglot
import sqlglot.expressions as exp
from typing import List, Set


def validate_sql(sql: str) -> bool:
    """Validate whether the SQL statement is syntax-valid for SQLite dialect."""
    try:
        sqlglot.parse_one(sql, read="sqlite")
        return True
    except Exception:
        return False


def format_sql(sql: str) -> str:
    """Format and prettify SQL query."""
    try:
        return sqlglot.transpile(sql, read="sqlite", write="sqlite", pretty=True)[0]
    except Exception:
        return sql


def extract_tables(sql: str) -> Set[str]:
    """Extract all table names reference in SQL query."""
    try:
        parsed = sqlglot.parse_one(sql, read="sqlite")
        return {table.name for table in parsed.find_all(exp.Table)}
    except Exception:
        return set()


def extract_columns(sql: str) -> Set[str]:
    """Extract all referenced column names in SQL query."""
    try:
        parsed = sqlglot.parse_one(sql, read="sqlite")
        return {col.name for col in parsed.find_all(exp.Column)}
    except Exception:
        return set()


def is_select_query(sql: str) -> bool:
    """Verify if the SQL statement is a SELECT query."""
    try:
        parsed = sqlglot.parse_one(sql, read="sqlite")
        return isinstance(parsed, exp.Select)
    except Exception:
        return sql.strip().lower().startswith("select")
