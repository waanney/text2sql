import os
import sys
import argparse
import difflib
from pathlib import Path

# Insert project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.io_utils import load_jsonl, load_json, save_jsonl
from common.logging_utils import log_event


def compute_features(question, column_name, table_name, literals, col_profile):
    """Compute heuristic/similarity features between question and schema element."""
    col_full = f"{table_name}.{column_name}".lower()
    q_words = set(question.lower().split())
    
    # 1. Name overlap
    col_words = set(column_name.lower().split("_"))
    overlap = len(q_words.intersection(col_words)) / len(col_words) if col_words else 0
    
    # 2. Semantic sim mock (fuzzy ratio of column name to question words)
    sim = max([difflib.SequenceMatcher(None, w, column_name.lower()).ratio() for w in q_words]) if q_words else 0.0

    # 3. Literal matching
    literal_exact = 0
    literal_fuzzy = 0.0
    for lit in literals:
        lit_str = str(lit).lower()
        # check if it exists in column's top/example values
        for val_dict in col_profile.get("top_k_values", []):
            val_str = str(val_dict.get("value", "")).lower()
            if lit_str == val_str:
                literal_exact = 1
            ratio = difflib.SequenceMatcher(None, lit_str, val_str).ratio()
            literal_fuzzy = max(literal_fuzzy, ratio)

    # 4. Profile type match
    type_match = 1 if "TEXT" in col_profile.get("declared_type", "").upper() else 0

    return {
        "semantic_sim_question_column": round(sim, 4),
        "name_overlap": round(overlap, 4),
        "literal_exact_match": literal_exact,
        "literal_fuzzy_match": round(literal_fuzzy, 4),
        "profile_type_match": type_match,
        "query_log_support": 0.0
    }


def build_schema_ranker_data(valid_jsonl_path, split="train"):
    log_event("INFO", f"Building schema ranker data from {valid_jsonl_path}")
    samples = load_jsonl(valid_jsonl_path)

    parsed_dir = Path(__file__).resolve().parent.parent / "data" / "cache" / "parsed_sql" / split
    metadata_dir = Path(__file__).resolve().parent.parent / "data" / "processed" / "metadata"

    dataset_rows = []

    # Cache profiles to avoid reloading files
    db_profiles = {}

    for sample in samples:
        qid = sample["question_id"]
        db_id = sample["db_id"]
        question = sample["question"]

        parsed_file = parsed_dir / f"{qid}.json"
        if not parsed_file.exists():
            continue

        parsed = load_json(parsed_file)
        pos_columns = set(parsed.get("columns_used", []))
        pos_tables = set(parsed.get("tables_used", []))
        literals = parsed.get("literals_used", [])

        # Get DB profile
        if db_id not in db_profiles:
            profile_path = metadata_dir / db_id / "column_profiles.json"
            if profile_path.exists():
                db_profiles[db_id] = load_json(profile_path)
            else:
                db_profiles[db_id] = []

        profiles = db_profiles[db_id]
        if not profiles:
            continue

        # Group by table.column
        profiles_map = {f"{p['table_name']}.{p['column_name']}": p for p in profiles}

        # Build positive and negative candidates
        for full_name, col_prof in profiles_map.items():
            t_name = col_prof["table_name"]
            c_name = col_prof["column_name"]

            is_pos = full_name in pos_columns
            label = 2 if is_pos else 0

            # If not used, but table is used, maybe label 1
            if not is_pos and t_name in pos_tables:
                label = 1

            features = compute_features(question, c_name, t_name, literals, col_prof)

            dataset_rows.append({
                "question_id": qid,
                "db_id": db_id,
                "item_type": "column",
                "candidate": full_name,
                "features": features,
                "label": label
            })

    output_path = Path(__file__).resolve().parent.parent / "data" / "processed" / "schema_ranker" / f"schema_ranker_{split}.jsonl"
    save_jsonl(dataset_rows, str(output_path))
    log_event("INFO", f"Saved {len(dataset_rows)} schema ranker rows to {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--valid_jsonl", default="data/processed/validation/valid_train.jsonl")
    parser.add_argument("--split", default="train")
    args = parser.parse_args()

    build_schema_ranker_data(args.valid_jsonl, args.split)
