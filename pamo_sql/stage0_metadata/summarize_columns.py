import json
from pathlib import Path
from common.llm_client import call_llm, clean_json_response


def build_column_summary_prompt(profile_item):
    return f"""
You are helping a Text-to-SQL system understand database columns.

Given this column profile, write:
1. short_description: one sentence about column meaning
2. value_format: how values are formatted
3. possible_semantic_type: e.g. id, name, date, amount, category, boolean, code

Column profile:
{json.dumps(profile_item, ensure_ascii=False, indent=2)}

Return JSON only.
"""


def summarize_profile(profile_path: str, output_path: str):
    with open(profile_path, "r", encoding="utf-8") as f:
        profiles = json.load(f)
    results = []

    for item in profiles:
        prompt = build_column_summary_prompt(item)
        response = call_llm(prompt)
        try:
            summary = clean_json_response(response)
        except Exception:
            summary = {"raw_response": response}

        item.update(summary)
        results.append(item)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
