import json
from pathlib import Path


def evaluate_cost(predictions_path, cost_per_1k_input=0.003, cost_per_1k_output=0.015):
    """
    Estimate LLM API cost from token usage metadata.
    """
    predictions = json.load(open(predictions_path, "r", encoding="utf-8"))

    results = []
    total_input_tokens = 0
    total_output_tokens = 0

    for pred in predictions:
        gen_meta = pred.get("generation_metadata", {})
        input_tokens = gen_meta.get("input_tokens", 0)
        output_tokens = gen_meta.get("output_tokens", 0)

        repair_input = sum(
            r.get("input_tokens", 0) for r in pred.get("repair_history", [])
        )
        repair_output = sum(
            r.get("output_tokens", 0) for r in pred.get("repair_history", [])
        )

        q_input = input_tokens + repair_input
        q_output = output_tokens + repair_output
        q_cost = (q_input / 1000 * cost_per_1k_input) + (q_output / 1000 * cost_per_1k_output)

        total_input_tokens += q_input
        total_output_tokens += q_output

        results.append({
            "question_id": pred["question_id"],
            "input_tokens": q_input,
            "output_tokens": q_output,
            "estimated_cost_usd": round(q_cost, 6),
        })

    total_cost = (
        (total_input_tokens / 1000 * cost_per_1k_input)
        + (total_output_tokens / 1000 * cost_per_1k_output)
    )

    summary = {
        "total_questions": len(results),
        "total_input_tokens": total_input_tokens,
        "total_output_tokens": total_output_tokens,
        "total_cost_usd": round(total_cost, 4),
        "avg_cost_per_question_usd": round(total_cost / max(len(results), 1), 6),
        "details": results,
    }

    return summary
