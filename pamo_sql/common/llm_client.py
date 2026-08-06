import os
import json
import re
from typing import Any, Dict

_local_pipeline = None

def get_local_pipeline():
    """
    Lazy load local Hugging Face CausalLM model on CUDA GPU.
    Default model: Qwen/Qwen2.5-Coder-7B-Instruct (state-of-the-art open model for Text-to-SQL).
    """
    global _local_pipeline
    if _local_pipeline is None:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline

        model_name = os.environ.get("LOCAL_MODEL_NAME", "Qwen/Qwen2.5-Coder-14B-Instruct")
        print(f"[llm_client] Loading local model '{model_name}' on GPU (CUDA)...")
        
        tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
        torch_dtype = torch.bfloat16 if torch.cuda.is_available() and torch.cuda.is_bf16_supported() else torch.float16
        
        try:
            # Try loading with device_map="auto" (requires accelerate)
            model = AutoModelForCausalLM.from_pretrained(
                model_name,
                dtype=torch_dtype,
                device_map="auto",
                trust_remote_code=True
            )
        except Exception as e:
            print(f"[llm_client] Warning: device_map='auto' failed ({e}). Loading model directly to CUDA...")
            model = AutoModelForCausalLM.from_pretrained(
                model_name,
                dtype=torch_dtype,
                trust_remote_code=True
            )
            if torch.cuda.is_available():
                model = model.to("cuda")

        _local_pipeline = pipeline(
            "text-generation",
            model=model,
            tokenizer=tokenizer
        )
        print(f"[llm_client] Local model '{model_name}' loaded successfully on GPU!")
    return _local_pipeline


def call_llm(prompt: str, temperature: float = 0.2) -> str:
    """
    Call LLM using:
    1. Local OpenAI-compatible server (vLLM / Ollama) if OPENAI_API_BASE is set.
    2. OpenAI API if OPENAI_API_KEY is set.
    3. Direct local GPU Hugging Face inference if CUDA is available or USE_LOCAL_LLM=1.
    4. Fallback mock response if offline / CPU only without keys.
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    base_url = os.environ.get("OPENAI_API_BASE")
    use_local_llm = os.environ.get("USE_LOCAL_LLM", "0").lower() in ("1", "true", "yes")
    
    # Mode 1: OpenAI API or Local vLLM/Ollama Server via OpenAI Client
    if (api_key or base_url) and not use_local_llm:
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
            print(f"[llm_client] Remote API call error: {e}. Switching to local GPU inference...")

    # Mode 2: Direct Local GPU Model via Hugging Face Transformers
    try:
        import torch
        if torch.cuda.is_available() or use_local_llm:
            pipe = get_local_pipeline()
            messages = [{"role": "user", "content": prompt}]
            outputs = pipe(
                messages,
                max_new_tokens=2048,
                temperature=temperature if temperature > 0 else 0.01,
                do_sample=temperature > 0,
            )
            generated_text = outputs[0]["generated_text"]
            if isinstance(generated_text, list):
                content = generated_text[-1].get("content", "")
            else:
                content = str(generated_text)
            return content.strip()
    except Exception as e:
        print(f"[llm_client] Local GPU inference error: {e}. Falling back to mock response.")

    # Mode 3: Fallback/mock responses for development/offline testing
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
