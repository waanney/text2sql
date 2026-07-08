import itertools
import json
from pathlib import Path
from common.execution_utils import normalize_result


def label_candidate(candidate_result, gold_result):
    """
    Label a candidate by comparing its execution result to the gold result.

    Returns:
        2 = correct (execution result matches gold)
        1 = partially plausible (same shape but different values)
        0 = wrong
    """
    if not candidate_result.get("success"):
        return 0

    pred_rows = normalize_result(candidate_result.get("sample_rows", []))
    gold_rows = normalize_result(gold_result.get("rows", []))

    if pred_rows == gold_rows:
        return 2

    # Weak label: same shape
    if (candidate_result.get("row_count") == gold_result.get("row_count")
            and candidate_result.get("column_count") == gold_result.get("column_count")):
        return 1

    return 0


def compact_context_for_selector(context):
    """Compact context to keep only what the selector needs."""
    return {
        "intent": context.get("intent"),
        "matched_values": context.get("matched_values", []),
        "evidence_constraints": context.get("evidence_constraints", []),
        "top_columns": context.get("top_columns", [])[:30],
        "top_joins": context.get("top_joins", [])[:10],
        "business_rules": context.get("business_rules", [])[:10]
    }


def compact_candidate_for_selector(candidate):
    """Compact candidate to keep only what the selector needs."""
    ex = candidate.get("execution_metadata", {})
    return {
        "candidate_id": candidate["candidate_id"],
        "source": candidate.get("source"),
        "sql": candidate["sql"],
        "execution": {
            "success": ex.get("success"),
            "error": ex.get("error"),
            "row_count": ex.get("row_count"),
            "column_count": ex.get("column_count"),
            "columns": ex.get("columns"),
            "sample_rows": (ex.get("sample_rows") or [])[:5],
            "runtime_sec": ex.get("runtime_sec"),
            "is_empty": ex.get("is_empty")
        },
        "repair_history": candidate.get("repair_history", [])
    }


def build_pairs_for_question(context, candidates):
    """Build pairwise preference pairs from labeled candidates."""
    pairs = []

    for a, b in itertools.combinations(candidates, 2):
        la = a["candidate_label"]
        lb = b["candidate_label"]

        if la == lb:
            winner = "tie"
        elif la > lb:
            winner = "A"
        else:
            winner = "B"

        pairs.append({
            "question_id": context["question_id"],
            "db_id": context["db_id"],
            "question": context["question"],
            "evidence": context.get("evidence"),
            "context": compact_context_for_selector(context),
            "candidate_a": compact_candidate_for_selector(a),
            "candidate_b": compact_candidate_for_selector(b),
            "winner": winner,
            "label_a": la,
            "label_b": lb
        })

    return pairs


def build_pairwise_dataset(contexts_dir, candidates_dir, gold_path, output_path):
    """
    Build full pairwise dataset from all questions.

    Args:
        contexts_dir: directory containing {qid}_context.json files
        candidates_dir: directory containing {qid}_repaired.json files
        gold_path: path to gold SQL/results JSON
        output_path: output JSONL file path
    """
    with open(gold_path, "r", encoding="utf-8") as f:
        golds = json.load(f)
    gold_map = {g["question_id"]: g for g in golds}

    all_pairs = []
    contexts_path = Path(contexts_dir)
    candidates_path = Path(candidates_dir)

    for ctx_file in sorted(contexts_path.glob("*_context.json")):
        with open(ctx_file, "r", encoding="utf-8") as f:
            context = json.load(f)

        qid = context["question_id"]
        cand_file = candidates_path / f"{qid}_repaired.json"
        if not cand_file.exists():
            continue

        with open(cand_file, "r", encoding="utf-8") as f:
            candidates = json.load(f)

        gold = gold_map.get(qid)
        if not gold:
            continue

        # Label each candidate
        for c in candidates:
            c["candidate_label"] = label_candidate(
                c.get("execution_metadata", {}), gold
            )

        pairs = build_pairs_for_question(context, candidates)
        all_pairs.extend(pairs)

    # Write JSONL
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for pair in all_pairs:
            f.write(json.dumps(pair, ensure_ascii=False) + "\n")

    print(f"[build_pairwise_dataset] {len(all_pairs)} pairs written to {output_path}")
    return all_pairs
