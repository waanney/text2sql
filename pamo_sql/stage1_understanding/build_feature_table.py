import pandas as pd


def build_column_feature_table(
    question_info,
    candidate_columns,
    literal_matches,
    query_log_features=None
):
    rows = []

    literal_hit_set = {
        (m["table"], m["column"]) for m in literal_matches
    }

    output_phrase = str(question_info.get("output_phrase", ""))
    
    filter_list = question_info.get("filter_phrases", [])
    if not isinstance(filter_list, list):
        filter_list = [filter_list]
    filter_phrases_strs = []
    for x in filter_list:
        if isinstance(x, dict):
            filter_phrases_strs.append(" ".join(str(v) for v in x.values() if v))
        elif x:
            filter_phrases_strs.append(str(x))
    filter_phrases = " ".join(filter_phrases_strs)

    for item in candidate_columns:
        table = item["table"]
        column = item["column"]
        profile = item["profile"]

        has_literal_match = int((table, column) in literal_hit_set)

        col_name_text = f"{table} {column} {profile.get('short_description', '')}"

        output_match = simple_text_overlap(output_phrase, col_name_text)
        filter_match = simple_text_overlap(filter_phrases, col_name_text)

        profile_type = profile.get("possible_semantic_type", "")
        is_id_like = int("id" in column.lower() or profile_type == "id")
        is_date_like = int("date" in column.lower() or profile_type == "date")
        is_numeric_like = int(profile.get("data_type", "").lower() in ["int", "integer", "real", "float"])

        log_support = compute_log_support(table, column, query_log_features)

        rows.append({
            "table": table,
            "column": column,
            "semantic_score": item["semantic_score"],
            "literal_match": has_literal_match,
            "output_match": output_match,
            "filter_match": filter_match,
            "is_id_like": is_id_like,
            "is_date_like": is_date_like,
            "is_numeric_like": is_numeric_like,
            "null_ratio": profile.get("null_ratio", 0),
            "distinct_count": profile.get("distinct_count", 0),
            "query_log_support": log_support,
        })

    return pd.DataFrame(rows)


def simple_text_overlap(a: str, b: str) -> float:
    a_words = set(a.lower().replace("_", " ").split())
    b_words = set(b.lower().replace("_", " ").split())
    if not a_words:
        return 0.0
    return len(a_words & b_words) / len(a_words)


def compute_log_support(table, column, query_log_features):
    if not query_log_features:
        return 0.0

    count = 0
    total = 0
    key1 = f"{table}.{column}".lower()
    key2 = column.lower()

    for item in query_log_features:
        total += 1
        cols_list = item.get("columns", [])
        if not isinstance(cols_list, list):
            cols_list = [cols_list]
        cols = " ".join(str(c) for c in cols_list).lower()
        if key1 in cols or key2 in cols:
            count += 1

    return count / total if total else 0.0
