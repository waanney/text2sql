"""
Round-robin tournament for SQL candidate selection.
"""

import itertools
from stage4_sql_prm_selection.build_pairwise_dataset import (
    compact_context_for_selector,
    compact_candidate_for_selector
)


def run_round_robin_tournament(context, candidates, selector):
    """
    Run pairwise round-robin tournament between all SQL candidates.

    Args:
        context: context package dict
        candidates: list of candidate dicts (with execution_metadata)
        selector: object with .compare(pair) method (SQLPRMSelector or LLMPairwiseSelector)

    Returns:
        ranked: list of (candidate_id, score) sorted descending
        comparison_logs: list of comparison result dicts
    """
    scores = {c["candidate_id"]: 0.0 for c in candidates}
    comparison_logs = []

    for a, b in itertools.combinations(candidates, 2):
        pair = {
            "question_id": context["question_id"],
            "db_id": context["db_id"],
            "question": context["question"],
            "evidence": context.get("evidence"),
            "context": compact_context_for_selector(context),
            "candidate_a": compact_candidate_for_selector(a),
            "candidate_b": compact_candidate_for_selector(b)
        }

        result = selector.compare(pair)
        winner = result["winner"]
        conf = result["confidence"]

        if winner == "A":
            scores[a["candidate_id"]] += conf
        elif winner == "B":
            scores[b["candidate_id"]] += conf
        else:
            scores[a["candidate_id"]] += 0.5 * conf
            scores[b["candidate_id"]] += 0.5 * conf

        comparison_logs.append({
            "candidate_a": a["candidate_id"],
            "candidate_b": b["candidate_id"],
            "winner": winner,
            "confidence": conf,
            "probs": result.get("probs"),
        })

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return ranked, comparison_logs
