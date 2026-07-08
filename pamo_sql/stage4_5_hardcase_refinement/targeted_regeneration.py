"""
Targeted regeneration for hard cases.
Instead of regenerating blindly, regenerate based on diagnosed errors.
"""

import json
from common.llm_client import call_llm, clean_json_response


def summarize_candidate_errors(candidates):
    """Build a summary of errors across current candidates."""
    errors = []
    for c in candidates:
        ex = c.get("execution_metadata", {})
        if not ex.get("success"):
            errors.append({
                "source": c.get("source"),
                "error": ex.get("error"),
                "sql": c["sql"][:200]
            })
        elif ex.get("is_empty"):
            errors.append({
                "source": c.get("source"),
                "issue": "empty_result",
                "sql": c["sql"][:200]
            })
    return errors


def targeted_regeneration(context, candidates, ddl_schema, n=5):
    """
    Generate new SQL candidates that specifically fix issues found in existing candidates.
    """
    error_summary = summarize_candidate_errors(candidates)

    prompt = f"""
The current SQL candidates are uncertain or likely wrong.

Question:
{context['question']}

Evidence:
{context.get('evidence')}

Evidence constraints:
{json.dumps(context.get('evidence_constraints', []), ensure_ascii=False)}

Matched values:
{json.dumps(context.get('matched_values', []), ensure_ascii=False)}

Relevant columns:
{json.dumps(context.get('top_columns', [])[:20], ensure_ascii=False)}

Relevant joins:
{json.dumps(context.get('top_joins', []), ensure_ascii=False)}

DDL schema:
{ddl_schema}

Error summary from previous candidates:
{json.dumps(error_summary, ensure_ascii=False, indent=2)}

Generate {n} new SQL candidates that specifically fix these issues.
Return a JSON list of SQL strings only.
"""
    response = call_llm(prompt, temperature=0.4)

    try:
        sql_list = clean_json_response(response)
        if isinstance(sql_list, str):
            sql_list = [sql_list]
    except Exception:
        # Fallback: treat response as single SQL
        sql_list = [response.strip()]

    new_candidates = []
    for i, sql in enumerate(sql_list[:n]):
        new_candidates.append({
            "sql": sql.strip() if isinstance(sql, str) else str(sql),
            "source": "targeted_regeneration",
            "prompt_id": f"hardcase_regen_v1_{i}",
            "candidate_id": f"{context['question_id']}_hardcase_{i}",
            "question_id": context["question_id"],
            "db_id": context["db_id"],
        })

    return new_candidates
