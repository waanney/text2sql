import time
from common.llm_client import call_llm
from stage3_execution_repair.sql_revisor import build_repair_prompt

def fix_sql_query(sql: str, error_msg: str, schema_info: str) -> dict:
    start_time = time.time()
    prompt = build_repair_prompt(sql, error_msg, schema_info)
    fixed_sql = call_llm(prompt, temperature=0.1)
    
    # Estimate tokens (rough baseline for evaluation cost tracking)
    input_tokens = len(prompt.split()) * 1.3
    output_tokens = len(fixed_sql.split()) * 1.3
    
    return {
        "fixed_sql": fixed_sql.strip(),
        "repair_time_sec": time.time() - start_time,
        "input_tokens": int(input_tokens),
        "output_tokens": int(output_tokens)
    }
