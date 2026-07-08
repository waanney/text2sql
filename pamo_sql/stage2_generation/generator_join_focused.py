from common.llm_client import call_llm


def generate_join_focused_sql(context, ddl_schema, n=3):
    """Generate SQL with special attention to join paths."""
    prompt = f"""
Generate SQL with special attention to join paths.

Question:
{context['question']}

Required/relevant joins:
{context.get('top_joins', [])}

Relevant columns:
{context.get('top_columns', [])[:25]}

Matched values:
{context.get('matched_values', [])}

DDL schema:
{ddl_schema}

Rules:
- Prefer verified join paths.
- Avoid joining on columns only because names look similar.
- If multiple tables are needed, use the shortest high-confidence join path.
- Return only SQL.
"""

    candidates = []
    for i in range(n):
        sql = call_llm(prompt, temperature=0.2 + 0.2 * i)
        candidates.append({
            "sql": sql,
            "source": "join_focused_generator",
            "prompt_id": f"join_focused_v1_{i}"
        })
    return candidates
