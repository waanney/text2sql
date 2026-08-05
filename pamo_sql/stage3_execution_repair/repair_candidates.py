from stage3_execution_repair.execute_sql import execute_sql
from stage3_execution_repair.diagnose_error import diagnose_sqlite_error
from stage3_execution_repair.sql_fixer import fix_sql_query

def repair_all_candidates(candidates, db_path, ddl_schema, max_rounds=2, use_repair=True):
    repaired_candidates = []

    for c in candidates:
        candidate = c.copy()
        history = []
        sql = candidate["sql"]
        rounds = 0
        success = False
        exec_meta = {}

        while rounds <= max_rounds:
            exec_meta = execute_sql(db_path, sql)
            # If query succeeded and returned rows, it is valid
            if exec_meta["success"] and not exec_meta.get("is_empty", False):
                success = True
                break
            
            if not use_repair or rounds == max_rounds:
                success = exec_meta["success"]
                break
            
            # Diagnose & Repair (Syntax Error or Empty Result Set)
            if not exec_meta["success"]:
                error_msg = exec_meta["error"]
            else:
                error_msg = "Query executed successfully, but returned 0 rows (empty result). Please check table JOIN conditions, filter column values, and comparison operators."

            diag = diagnose_sqlite_error(error_msg)
            repair_result = fix_sql_query(sql, error_msg, ddl_schema)
            
            history.append({
                "round": rounds + 1,
                "original_sql": sql,
                "error": error_msg,
                "diagnosis": diag,
                "fixed_sql": repair_result["fixed_sql"],
                "repair_time_sec": repair_result["repair_time_sec"],
                "input_tokens": repair_result["input_tokens"],
                "output_tokens": repair_result["output_tokens"]
            })
            
            sql = repair_result["fixed_sql"]
            rounds += 1
        
        candidate["sql"] = sql
        candidate["execution_metadata"] = exec_meta
        candidate["repair_history"] = history
        repaired_candidates.append(candidate)

    return repaired_candidates
