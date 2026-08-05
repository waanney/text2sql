from common.llm_client import call_llm


def generate_reasoning_sql(context, ddl_schema, n=3):
    prompt = f"""
You are a Text-to-SQL reasoning model.

Question:
{context["question"]}

Evidence:
{context.get("evidence")}

Relevant columns:
{context["top_columns"]}

Matched database values:
{context["matched_values"]}

DDL schema:
{ddl_schema}

Think carefully about:
1. STRICT PROJECTION: SELECT ONLY the specific columns/attributes explicitly requested by the user question. Do NOT add extra metadata, ID, or intermediate calculation columns unless requested.
2. EVIDENCE BINDING: Use exact formulas provided in Evidence (e.g., if evidence defines rate = A / B, use CAST(A AS REAL) / B in SELECT/WHERE).
3. SUBQUERY STRUCTURE: If question asks for "the entity with the highest/lowest X", consider using nested subqueries WHERE col = (SELECT col FROM table ORDER BY X DESC LIMIT 1).
4. required filters, joins, aggregations, and SQLite dialect.

Return only SQL.
"""
    candidates = []
    for i in range(n):
        sql = call_llm(prompt, temperature=0.3 + i * 0.2)
        candidates.append({
            "sql": sql,
            "source": "reasoning_generator",
            "prompt_id": f"reasoning_v1_temp_{i}"
        })
    return candidates
