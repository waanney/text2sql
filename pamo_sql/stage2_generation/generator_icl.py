from common.llm_client import call_llm


def format_examples(examples):
    blocks = []
    for ex in examples:
        blocks.append(f"Question: {ex['question']}\nSQL: {ex['sql']}")
    return "\n\n".join(blocks)


def generate_icl_sql(context, light_schema, n=3):
    examples_text = format_examples(context.get("few_shot_examples", []))

    prompt = f"""
Generate SQL from the question using the schema and examples.

Schema:
{light_schema}

Examples:
{examples_text}

Question:
{context["question"]}

Return only SQL.
"""
    candidates = []
    for i in range(n):
        sql = call_llm(prompt, temperature=0.5 + i * 0.3)
        candidates.append({
            "sql": sql,
            "source": "icl_generator",
            "prompt_id": f"icl_v1_temp_{i}"
        })
    return candidates
