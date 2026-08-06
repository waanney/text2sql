import json
from common.llm_client import call_llm, clean_json_response


def extract_evidence_constraints(question, evidence, top_columns, column_profiles=None):
    """
    Parse evidence/oracle knowledge into SQL-grounded constraints.

    Returns a list of constraint dicts:
      - phrase: the evidence phrase
      - column: table.column
      - operator: =, >, <, >=, <=, LIKE, IN, etc.
      - value: the literal value
      - needs_cast: true/false
      - cast_type: REAL/INTEGER/TEXT/null
      - confidence: 0.0-1.0
    """
    if not evidence:
        return []

    col_info = json.dumps(top_columns[:30], ensure_ascii=False, indent=2) if top_columns else "[]"
    profile_info = json.dumps(column_profiles[:20], ensure_ascii=False, indent=2) if column_profiles else "[]"

    prompt = f"""
Convert evidence into SQL-grounded constraints.

Question:
{question}

Evidence:
{evidence}

Candidate columns:
{col_info}

Column profiles:
{profile_info}

Return a JSON list. Each item must have:
- phrase: the part of evidence being parsed
- column: table.column_name
- operator: SQL operator (=, >, <, >=, <=, LIKE, IN, !=, IS NULL, IS NOT NULL)
- value: the literal value to filter on
- needs_cast: true/false
- cast_type: REAL/INTEGER/TEXT/null
- confidence: 0.0 to 1.0

Return JSON only.
"""
    response = call_llm(prompt)
    try:
        constraints = clean_json_response(response)
        if isinstance(constraints, dict):
            constraints = [constraints]
        return constraints
    except Exception:
        return [{"raw_response": response, "parse_error": True}]
