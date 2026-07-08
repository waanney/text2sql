"""
Final selector: groups candidates, runs tournament, picks best SQL.
"""

import json
from pathlib import Path
from stage4_sql_prm_selection.tournament import run_round_robin_tournament


def select_final_sql(context, candidates, selector, output_path=None):
    """
    Select the best SQL candidate via pairwise tournament.

    Args:
        context: context package dict
        candidates: list of candidate dicts (with execution_metadata)
        selector: object with .compare(pair) method
        output_path: optional path to save selection output

    Returns:
        selection output dict with final_sql, rankings, logs
    """
    # Group by execution result to reduce comparisons
    representatives = group_by_execution_result(candidates)

    ranked, comparison_logs = run_round_robin_tournament(
        context=context,
        candidates=representatives,
        selector=selector
    )

    best_id = ranked[0][0]
    best_candidate = next(c for c in representatives if c["candidate_id"] == best_id)

    output = {
        "question_id": context["question_id"],
        "db_id": context["db_id"],
        "final_sql": best_candidate["sql"],
        "best_candidate_id": best_id,
        "ranked_candidates": ranked,
        "comparison_logs": comparison_logs,
        "selected_candidate": best_candidate,
        "num_original_candidates": len(candidates),
        "num_representatives": len(representatives),
    }

    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2, default=str)

    return output


def group_by_execution_result(candidates):
    """Deduplicate candidates that produce the same execution result."""
    groups = {}
    for c in candidates:
        ex = c.get("execution_metadata", {})
        key = (
            str(ex.get("sample_rows"))
            + "|" + str(ex.get("row_count"))
            + "|" + str(ex.get("column_count"))
        )
        if key not in groups:
            groups[key] = c
        else:
            groups[key] = choose_representative(groups[key], c)
    return list(groups.values())


def choose_representative(a, b):
    """Pick the better representative from two same-result candidates."""
    source_priority = {
        "metadata_constrained_generator": 5,
        "evidence_focused_generator": 5,
        "reasoning_generator": 4,
        "join_focused_generator": 4,
        "icl_generator": 3,
        "simple_generator": 2
    }

    score_a = source_priority.get(a.get("source"), 0) - len(a.get("repair_history", []))
    score_b = source_priority.get(b.get("source"), 0) - len(b.get("repair_history", []))

    return a if score_a >= score_b else b
