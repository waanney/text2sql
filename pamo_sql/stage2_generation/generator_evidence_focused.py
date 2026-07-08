from common.llm_client import call_llm


def generate_evidence_focused_sql(context, ddl_schema, n=3):
    """Generate SQL that explicitly satisfies all evidence/oracle constraints."""
    prompt = f"""
Generate SQL. You must explicitly satisfy all evidence constraints.

Question:
{context['question']}

Evidence:
{context.get('evidence')}

Parsed evidence constraints:
{context.get('evidence_constraints', [])}

Matched values:
{context.get('matched_values', [])}

Relevant columns:
{context.get('top_columns', [])[:25]}

DDL schema:
{ddl_schema}

Rules:
- If evidence says a phrase maps to a column/operator/value, use it.
- If a numeric comparison is applied to a TEXT column, consider CAST.
- Do not ignore evidence.
- Return only SQL.
"""

    candidates = []
    for i in range(n):
        sql = call_llm(prompt, temperature=0.2 + 0.2 * i)
        candidates.append({
            "sql": sql,
            "source": "evidence_focused_generator",
            "prompt_id": f"evidence_focused_v1_{i}"
        })
    return candidates
