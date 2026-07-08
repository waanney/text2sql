"""
Detect hard cases where the selector is uncertain or the result is suspicious.
"""


def is_hard_case(selection_output, candidates, context):
    """
    Determine if a question is a hard case needing refinement.

    Triggers:
      - Low margin between top-1 and top-2 candidates
      - All top candidates return empty results
      - Evidence constraints not covered by the selected SQL
    """
    ranked = selection_output.get("ranked_candidates", [])

    if len(ranked) < 2:
        return False

    top_score = ranked[0][1]
    second_score = ranked[1][1]
    margin = top_score - second_score

    # Low margin → selector uncertain
    if margin < 0.5:
        return True

    # All top candidates return empty
    top_ids = {x[0] for x in ranked[:3]}
    top_candidates = [c for c in candidates if c["candidate_id"] in top_ids]
    if all(c.get("execution_metadata", {}).get("is_empty") for c in top_candidates):
        return True

    # Evidence constraints not covered by top SQL
    final_sql = selection_output.get("final_sql", "")
    evidence_constraints = context.get("evidence_constraints", [])
    if evidence_constraints and not covers_evidence_constraints(final_sql, evidence_constraints):
        return True

    return False


def covers_evidence_constraints(sql, evidence_constraints):
    """
    Heuristic check: does the SQL mention the columns/values from evidence constraints?
    """
    sql_lower = sql.lower()
    for constraint in evidence_constraints:
        if constraint.get("parse_error"):
            continue
        col = constraint.get("column", "")
        value = str(constraint.get("value", ""))

        # Check if column name (after the dot) appears in SQL
        col_name = col.split(".")[-1].lower() if "." in col else col.lower()
        if col_name and col_name not in sql_lower:
            return False

        # Check if value appears in SQL
        if value and value.lower() not in sql_lower:
            return False

    return True
