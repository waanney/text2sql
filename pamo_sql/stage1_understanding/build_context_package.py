import json
from pathlib import Path


def build_context_package(
    question_input,
    question_info,
    ranked_columns,
    literal_matches,
    evidence_constraints=None,
    top_joins=None,
    business_rules=None,
    few_shot_examples=None,
    top_k_columns=30
):
    top_cols = ranked_columns.head(top_k_columns).to_dict(orient="records")

    top_tables = []
    seen_tables = set()
    for col in top_cols:
        table = col["table"]
        if table not in seen_tables:
            seen_tables.add(table)
            top_tables.append({
                "table": table,
                "score": float(col["relevance_score"])
            })

    # Compute multi-dimensional confidence
    max_col_score = float(ranked_columns["relevance_score"].max())
    literal_conf = 1.0 if literal_matches else 0.0
    evidence_conf = 0.0
    if evidence_constraints:
        valid = [c for c in evidence_constraints if not c.get("parse_error")]
        if valid:
            evidence_conf = sum(c.get("confidence", 0) for c in valid) / len(valid)

    context = {
        "question_id": question_input["question_id"],
        "db_id": question_input["db_id"],
        "question": question_input["question"],
        "evidence": question_input.get("evidence"),
        "intent": question_info,
        "literals": question_info.get("literals", []),
        "matched_values": literal_matches,
        "evidence_constraints": evidence_constraints or [],
        "top_tables": top_tables,
        "top_columns": top_cols,
        "top_joins": top_joins or [],
        "business_rules": business_rules or [],
        "few_shot_examples": few_shot_examples or [],
        "confidence": {
            "schema_linking": max_col_score,
            "literal_mapping": literal_conf,
            "evidence_parsing": evidence_conf,
        }
    }

    return context


def save_context(context, output_path):
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(context, f, ensure_ascii=False, indent=2)
