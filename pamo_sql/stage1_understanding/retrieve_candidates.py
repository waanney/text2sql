import json
from difflib import SequenceMatcher


def fuzzy_score(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def retrieve_literal_matches(literals, column_summaries, threshold=0.75):
    matches = []
    
    # Safely convert literals to a list of strings
    safe_literals = []
    if not isinstance(literals, list):
        literals = [literals]
    for lit in literals:
        if isinstance(lit, dict):
            safe_literals.extend([str(v) for v in lit.values() if v])
        elif lit:
            safe_literals.append(str(lit))

    for lit in safe_literals:
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
    output_phrase = str(question_info.get("output_phrase") or "")
    
    filter_phrases = question_info.get("filter_phrases", [])
    if not isinstance(filter_phrases, list):
        filter_phrases = [filter_phrases]
    filter_phrases_strs = []
    for x in filter_phrases:
        if isinstance(x, dict):
            filter_phrases_strs.append(" ".join(str(v) for v in x.values() if v))
        elif x:
            filter_phrases_strs.append(str(x))
            
    literals = question_info.get("literals", [])
    if not isinstance(literals, list):
        literals = [literals]
    literals_strs = []
    for x in literals:
        if isinstance(x, dict):
            literals_strs.append(" ".join(str(v) for v in x.values() if v))
        elif x:
            literals_strs.append(str(x))

    q_text = " ".join([
        output_phrase,
        " ".join(filter_phrases_strs),
        " ".join(literals_strs)
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
