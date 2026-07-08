def diagnose_sqlite_error(error_msg: str) -> str:
    """Diagnose SQL error and return a helpful category/suggestion."""
    err_lower = error_msg.lower()
    if "no such column" in err_lower:
        return "column_missing"
    if "no such table" in err_lower:
        return "table_missing"
    if "syntax error" in err_lower:
        return "syntax_error"
    return "unknown_execution_error"
