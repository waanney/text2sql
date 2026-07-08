import json
from difflib import SequenceMatcher


def fuzzy_score(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def retrieve_literal_matches(literals, column_summaries, threshold=0.75):
    matches = []

    for lit in literals:
        for col in column_summaries:
            top_values = col.get("top_values", [])
            for tv in top_values:
                value = str(tv.get("value", ""))
                score = fuzzy_score(lit, value)
                if score >= threshold:
                    matches.append({
                        "literal": lit,
                        "table": col["table_name"],
                        "column": col["column_name"],
                        "matched_value": value,
                        "score": score
                    })

    return matches


def retrieve_candidate_columns(question_info, column_summaries, top_k=80):
    q_text = " ".join([
        question_info.get("output_phrase") or "",
        " ".join(question_info.get("filter_phrases", [])),
        " ".join(question_info.get("literals", []))
    ])

    scored = []
    for col in column_summaries:
        col_text = " ".join([
            col.get("table_name", ""),
            col.get("column_name", ""),
            col.get("short_description", ""),
            col.get("possible_semantic_type", "")
        ])
        score = fuzzy_score(q_text, col_text)
        scored.append({
            "table": col["table_name"],
            "column": col["column_name"],
            "semantic_score": score,
            "profile": col
        })

    scored.sort(key=lambda x: x["semantic_score"], reverse=True)
    return scored[:top_k]
