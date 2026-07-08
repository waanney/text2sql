"""
Execution utilities for normalizing and comparing SQL execution results.
"""

def normalize_result(rows):
    """Normalize execution result for comparison: sort rows and convert to tuples."""
    if rows is None:
        return None
    try:
        return sorted(set(tuple(str(v) for v in row) for row in rows))
    except Exception:
        return rows


def compact_execution_summary(exec_meta, max_sample_rows=5):
    """Create a compact execution summary suitable for selector input."""
    if exec_meta is None:
        exec_meta = {}
    return {
        "success": exec_meta.get("success"),
        "error": exec_meta.get("error"),
        "row_count": exec_meta.get("row_count"),
        "column_count": exec_meta.get("column_count"),
        "columns": exec_meta.get("columns"),
        "sample_rows": (exec_meta.get("sample_rows") or [])[:max_sample_rows],
        "runtime_sec": exec_meta.get("runtime_sec"),
        "is_empty": exec_meta.get("is_empty"),
    }
