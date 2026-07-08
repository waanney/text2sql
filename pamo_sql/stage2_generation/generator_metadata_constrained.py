from common.llm_client import call_llm


def generate_metadata_constrained_sql(context, ddl_schema, n=2):
    allowed_columns = [
        f'{c["table"]}.{c["column"]}' for c in context["top_columns"][:25]
    ]

    prompt = f"""
You must generate SQL using only the grounded database context.

Question:
{context["question"]}

Allowed/relevant columns:
{allowed_columns}

Matched literal values:
{context["matched_values"]}

Relevant joins:
{context.get("top_joins", [])}

Known business/query-log rules:
{context.get("business_rules", [])}

DDL schema:
{ddl_schema}

Rules:
- Prefer matched columns for literal filters.
- Prefer verified join paths.
- Do not invent column names.
- If a literal is matched to a specific column, use that column.
- Return only SQL.
"""
    candidates = []
    for i in range(n):
        sql = call_llm(prompt, temperature=0.2 + i * 0.2)
        candidates.append({
            "sql": sql,
            "source": "metadata_constrained_generator",
            "prompt_id": f"metadata_constrained_v1_{i}"
        })
    return candidates
