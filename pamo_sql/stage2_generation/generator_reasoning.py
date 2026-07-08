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
1. required output
2. filters
3. joins
4. aggregation
5. SQL dialect

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
