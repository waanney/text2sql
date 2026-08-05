import re
import sqlglot
import sqlglot.expressions as exp
from typing import List, Set


def clean_sql(sql: str) -> str:
    """Clean markdown code block wrappers and strip trailing/leading whitespace."""
    if not sql:
        return ""
    # Strip markdown block ```sql ... ``` or ``` ... ```
    cleaned = re.sub(r"^```(?:sql)?\s*", "", sql.strip(), flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned, flags=re.IGNORECASE)
    return cleaned.strip()


def validate_sql(sql: str) -> bool:
    """Validate whether the SQL statement is syntax-valid for SQLite dialect."""
    try:
        cleaned = clean_sql(sql)
        sqlglot.parse_one(cleaned, read="sqlite")
        return True
    except Exception:
        return False


def format_sql(sql: str) -> str:
    """Format and prettify SQL query."""
    cleaned = clean_sql(sql)
    try:
        return sqlglot.transpile(cleaned, read="sqlite", write="sqlite", pretty=True)[0]
    except Exception:
        return cleaned


def extract_tables(sql: str) -> Set[str]:
    """Extract all table names reference in SQL query."""
    try:
        cleaned = clean_sql(sql)
        parsed = sqlglot.parse_one(cleaned, read="sqlite")
        return {table.name for table in parsed.find_all(exp.Table)}
    except Exception:
        return set()


def extract_columns(sql: str) -> Set[str]:
    """Extract all referenced column names in SQL query."""
    try:
        cleaned = clean_sql(sql)
        parsed = sqlglot.parse_one(cleaned, read="sqlite")
        return {col.name for col in parsed.find_all(exp.Column)}
    except Exception:
        return set()


def is_select_query(sql: str) -> bool:
    """Verify if the SQL statement is a SELECT query."""
    cleaned = clean_sql(sql)
    try:
        parsed = sqlglot.parse_one(cleaned, read="sqlite")
        return isinstance(parsed, exp.Select)
    except Exception:
        return cleaned.lower().startswith("select")

