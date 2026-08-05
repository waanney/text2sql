"""
PAMO-SQL v2: End-to-end pipeline for a single question.

Flow:
  Stage 1: Profile-aware task understanding (+ evidence constraints)
  Stage 2: Multi-generator SQL generation (6 generators)
  Stage 3: Execution + repair loop
  Stage 4: SQL-PRM pairwise tournament selection
  Stage 4.5: Optional hard-case refinement
"""

import sys
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
# Setup sys.path to allow imports from pamo_sql root
pamo_sql_dir = Path(__file__).resolve().parent.parent
if str(pamo_sql_dir) not in sys.path:
    sys.path.insert(0, str(pamo_sql_dir))

from stage1_understanding.extract_question import extract_question_info
from stage1_understanding.extract_evidence_constraints import extract_evidence_constraints
from stage1_understanding.retrieve_candidates import retrieve_literal_matches, retrieve_candidate_columns
from stage1_understanding.build_feature_table import build_column_feature_table
from stage1_understanding.schema_ranker import rule_based_rank_columns
from stage1_understanding.build_context_package import build_context_package, save_context
from stage2_generation.generate_candidates import generate_all_candidates
from stage3_execution_repair.repair_candidates import repair_all_candidates
from stage4_sql_prm_selection.final_selector import select_final_sql
from stage4_sql_prm_selection.llm_tie_breaker import LLMPairwiseSelector
from stage4_5_hardcase_refinement.rerun_selection import rerun_selection_if_hard
from common.logging_utils import log_event


def run_single_question(
    question_input,
    db_path,
    column_summaries,
    ddl_schema,
    light_schema,
    selector=None,
    config=None,
    artifacts_dir=None
):
    """
    Run the full PAMO-SQL v2 pipeline for a single question.
    """
    config = config or {}
    stages = config.get("stages", {})
    q_id = question_input["question_id"]

    log_event("INFO", f"Starting PAMO-SQL pipeline for question: {q_id}", extra={"question_input": question_input})

    if artifacts_dir is None:
        artifacts_dir = str(pamo_sql_dir / "artifacts")

    # Default to LLM pairwise selector if none provided
    if selector is None:
        selector = LLMPairwiseSelector()

    # ─── Stage 1: Understanding ───────────────────────────────────
    log_event("INFO", "Running Stage 1: Understanding...")
    q_info = extract_question_info(
        question_input["question"],
        question_input.get("evidence")
    )

    literals = q_info.get("literals", [])
    literal_matches = retrieve_literal_matches(literals, column_summaries)
    candidate_cols = retrieve_candidate_columns(q_info, column_summaries)

    # Evidence constraints (new in v2)
    evidence_constraints = []
    if stages.get("use_evidence_constraints", True) and question_input.get("evidence"):
        log_event("DEBUG", "Parsing evidence constraints...")
        evidence_constraints = extract_evidence_constraints(
            question_input["question"],
            question_input["evidence"],
            [{"table": c["table"], "column": c["column"]} for c in candidate_cols[:30]],
            column_summaries[:20]
        )
        log_event("DEBUG", f"Extracted evidence constraints: {evidence_constraints}")

    # Build features & rank
    feature_df = build_column_feature_table(q_info, candidate_cols, literal_matches)

    if stages.get("use_schema_ranker", True):
        ranked_df = rule_based_rank_columns(feature_df)
    else:
        ranked_df = feature_df.sort_values("semantic_score", ascending=False)
        ranked_df["relevance_score"] = ranked_df["semantic_score"]

    # Build enriched context package
    context = build_context_package(
        question_input, q_info, ranked_df, literal_matches,
        evidence_constraints=evidence_constraints
    )

    context_path = Path(artifacts_dir) / "stage1_context" / f"{q_id}_context.json"
    save_context(context, str(context_path))
    log_event("INFO", f"Stage 1 Complete. Context saved to {context_path}")

    # ─── Stage 2: Generation ──────────────────────────────────────
    log_event("INFO", "Running Stage 2: Candidate Generation...")
    candidates_path = Path(artifacts_dir) / "stage2_candidates" / f"{q_id}_candidates.json"
    candidates = generate_all_candidates(
        str(context_path), ddl_schema, light_schema,
        str(candidates_path), config
    )
    log_event("INFO", f"Stage 2 Complete. Generated {len(candidates)} candidates.")

    # ─── Stage 3: Execution + Repair ─────────────────────────────
    log_event("INFO", "Running Stage 3: Execution and Repair...")
    use_repair = stages.get("use_repair", True)
    repaired_candidates = repair_all_candidates(
        candidates, db_path, ddl_schema,
        max_rounds=2, use_repair=use_repair
    )

    repaired_path = Path(artifacts_dir) / "stage3_repaired" / f"{q_id}_repaired.json"
    repaired_path.parent.mkdir(parents=True, exist_ok=True)
    with open(repaired_path, "w", encoding="utf-8") as f:
        json.dump(repaired_candidates, f, ensure_ascii=False, indent=2)
    log_event("INFO", "Stage 3 Complete. Candidates executed and repaired.")

    # ─── Stage 4: SQL-PRM Selection ──────────────────────────────
    log_event("INFO", "Running Stage 4: Selection...")
    selection_path = Path(artifacts_dir) / "stage4_selection" / f"{q_id}_final.json"
    selection = select_final_sql(
        context=context,
        candidates=repaired_candidates,
        selector=selector,
        output_path=str(selection_path)
    )
    log_event("INFO", f"Stage 4 Complete. Final SQL selected: {selection.get('final_sql')}")

    # ─── Stage 4.5: Hard-case Refinement (optional) ──────────────
    if stages.get("use_hard_case_refinement", True):
        log_event("INFO", "Checking Stage 4.5: Hard-case Refinement...")
        refinement_path = Path(artifacts_dir) / "stage4_5_refinement" / f"{q_id}_refined.json"
        selection = rerun_selection_if_hard(
            selection_output=selection,
            context=context,
            candidates=repaired_candidates,
            selector=selector,
            ddl_schema=ddl_schema,
            db_path=db_path,
            output_path=str(refinement_path)
        )
        if selection.get("hard_case"):
            log_event("INFO", f"Stage 4.5 Refinement Triggered. New Final SQL: {selection.get('final_sql')}")
        else:
            log_event("INFO", "Stage 4.5 Refinement Not Triggered.")

    log_event("INFO", f"PAMO-SQL pipeline execution finished for question: {q_id}")
    return selection


if __name__ == "__main__":
    # Example dry-run
    sample_q = {
        "question_id": "test_001",
        "question": "What is the zip code of all charter schools in Fresno County Office of Education?",
        "db_id": "california_schools",
        "evidence": "charter school refers to Charter School (Y/N) = 1"
    }

    mock_summaries = [{
        "db_id": "california_schools",
        "table_name": "schools",
        "column_name": "Zip",
        "data_type": "text",
        "null_ratio": 0.0,
        "distinct_count": 500,
        "top_values": [{"value": "93720", "count": 5}],
        "short_description": "ZIP code of the school",
        "possible_semantic_type": "code"
    }, {
        "db_id": "california_schools",
        "table_name": "schools",
        "column_name": "District",
        "data_type": "text",
        "null_ratio": 0.0,
        "distinct_count": 100,
        "top_values": [{"value": "Fresno County Office of Education", "count": 10}],
        "short_description": "School district name",
        "possible_semantic_type": "name"
    }]

    mock_ddl = """
CREATE TABLE schools (Zip TEXT, District TEXT, CDSCode TEXT);
CREATE TABLE frpm (CDSCode TEXT, "Charter School (Y/N)" TEXT);
"""

    print("Running PAMO-SQL v2 dry-run...")
    result = run_single_question(
        question_input=sample_q,
        db_path="data/raw/databases/california_schools.sqlite",
        column_summaries=mock_summaries,
        ddl_schema=mock_ddl,
        light_schema=mock_ddl,
        config={
            "stages": {
                "use_evidence_constraints": True,
                "use_repair": False,
                "use_hard_case_refinement": False,
                "use_reasoning_generator": True,
                "use_icl_generator": False,
                "use_metadata_constrained_generator": False,
                "use_evidence_focused_generator": True,
                "use_join_focused_generator": False,
                "use_simple_generator": True,
            },
            "generation": {
                "reasoning_n": 1,
                "evidence_focused_n": 1,
                "simple_n": 1,
            }
        }
    )
    print(f"Final SQL: {result.get('final_sql')}")
    print("Dry-run complete.")
