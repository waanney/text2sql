"""
Orchestrator for hard-case refinement: detect → refine → re-select.
"""

from stage4_5_hardcase_refinement.detect_hard_case import is_hard_case
from stage4_5_hardcase_refinement.mcts_refinement import mcts_refinement
from stage4_sql_prm_selection.final_selector import select_final_sql


def rerun_selection_if_hard(
    selection_output, context, candidates, selector,
    ddl_schema, db_path, output_path=None
):
    """
    Check if the question is a hard case. If so, run targeted refinement
    and re-select from the expanded candidate pool.

    Returns:
        Updated selection output (either original or refined)
    """
    if not is_hard_case(selection_output, candidates, context):
        return selection_output

    # Run refinement
    refined_candidates = mcts_refinement(
        context=context,
        candidates=candidates,
        ddl_schema=ddl_schema,
        db_path=db_path,
        max_rounds=1,
        n_per_round=5
    )

    # Merge and re-select
    all_candidates = candidates + refined_candidates

    refined_selection = select_final_sql(
        context=context,
        candidates=all_candidates,
        selector=selector,
        output_path=output_path
    )

    refined_selection["hard_case"] = True
    refined_selection["num_refined_candidates"] = len(refined_candidates)

    return refined_selection
