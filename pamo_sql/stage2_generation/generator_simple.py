from common.llm_client import call_llm


def generate_simple_sql(context, light_schema, n=1):
    prompt = f"""
Generate the simplest valid SQL for this question.

Question:
{context["question"]}

Relevant schema:
{light_schema}

Relevant columns:
{context["top_columns"][:15]}

Return only SQL. Only SELECT the exact target attributes requested.
"""
    return [{
        "sql": call_llm(prompt, temperature=0),
        "source": "simple_generator",
        "prompt_id": "simple_v1"
    }]
