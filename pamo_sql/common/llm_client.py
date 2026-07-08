import os
import json
import re
from typing import Any, Dict

def call_llm(prompt: str, temperature: float = 0.2) -> str:
    """
    Call the LLM using standard OpenAI client or similar.
    Fallback to env variables or mock response if not configured.
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    base_url = os.environ.get("OPENAI_API_BASE")
    
    if api_key or base_url:
        try:
            from openai import OpenAI
            client = OpenAI(
                api_key=api_key or "local-model",
                base_url=base_url
            )
            model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"[llm_client] API call error: {e}. Falling back to mock/dummy response.")
    
    # Fallback/mock responses for development/offline testing
    prompt_lower = prompt.lower()
    if "extract structured information" in prompt_lower:
        return json.dumps({
            "output_phrase": "school name",
            "operation": "select",
            "literals": ["Fresno County Office of Education"],
            "filter_phrases": ["charter schools"],
            "aggregation": None,
            "time_phrases": [],
            "question_skeleton": "List the <column> of all <school_type> in <organization>."
        })
    elif "understand database columns" in prompt_lower:
        return json.dumps({
            "short_description": "Name or identifier of the school/agency.",
            "value_format": "text",
            "possible_semantic_type": "name"
        })
    elif "reasoning model" in prompt_lower or "grounded database context" in prompt_lower or "simplest valid sql" in prompt_lower:
        return "SELECT school_name FROM california_schools WHERE organization = 'Fresno County Office of Education' AND school_type = 'charter';"
    
    return "SELECT * FROM sqlite_master;"


def clean_json_response(response: str) -> Dict[str, Any]:
    """
    Cleans markdown code blocks (e.g. ```json ... ```) from LLM responses
    and parses it into a dictionary safely.
    """
    cleaned = response.strip()
    # Remove markdown code block wrappers
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.strip()
    try:
        return json.loads(cleaned)
    except Exception as e:
        # Try to find a JSON-like substring
        match = re.search(r"(\{.*\})", cleaned, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except Exception:
                pass
        raise ValueError(f"Failed to parse JSON response: {response}") from e
