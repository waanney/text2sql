from common.llm_client import call_llm, clean_json_response


def extract_question_info(question: str, evidence: str | None = None):
    prompt = f"""
Extract structured information for Text-to-SQL.

Question:
{question}

Evidence:
{evidence or ""}

Return JSON with:
- output_phrase
- operation: select/count/sum/average/rank/compare/filter
- literals: list of exact entities/values mentioned
- filter_phrases
- aggregation
- time_phrases
- question_skeleton
Return JSON only.
"""
    response = call_llm(prompt)
    return clean_json_response(response)
