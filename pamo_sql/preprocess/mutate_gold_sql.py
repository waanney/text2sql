import re
import random
import sqlglot
import sqlglot.expressions as exp


def mutate_sql(sql):
    """
    Generate multiple logically mutated versions of a SQL query.
    Returns a dictionary mapping mutation_type -> mutated_sql.
    """
    mutations = {}

    # Parse using sqlglot for structural manipulations
    try:
        parsed = sqlglot.parse_one(sql, read="sqlite")
    except Exception:
        # Fallback to text mutations if parse fails
        parsed = None

    # 1. Remove distinct
    if "distinct" in sql.lower():
        mutations["remove_distinct"] = re.sub(r"\bdistinct\b", "", sql, flags=re.IGNORECASE)

    # 2. Count star vs count distinct
    if "count(distinct" in sql.lower().replace(" ", ""):
        mutations["count_star_vs_count_distinct"] = re.sub(
            r"count\s*\(\s*distinct[^)]+\)", "COUNT(*)", sql, flags=re.IGNORECASE
        )

    # 3. Wrong order direction
    if "desc" in sql.lower():
        mutations["wrong_order_direction"] = re.sub(r"\bdesc\b", "ASC", sql, flags=re.IGNORECASE)
    elif "asc" in sql.lower():
        mutations["wrong_order_direction"] = re.sub(r"\basc\b", "DESC", sql, flags=re.IGNORECASE)

    # 4. Remove group by
    if "group by" in sql.lower():
        # Remove everything from group by to the end or to order/limit
        mutations["remove_group_by"] = re.sub(
            r"\bgroup\s+by\s+.*?(?=\border\s+by\b|\blimit\b|$)", "", sql, flags=re.IGNORECASE
        )

    # 5. Remove where condition
    if "where" in sql.lower():
        mutations["remove_where_condition"] = re.sub(
            r"\bwhere\s+.*?(?=\bgroup\s+by\b|\border\s+by\b|\blimit\b|$)", "", sql, flags=re.IGNORECASE
        )

    # 6. Replace aggregation
    if parsed:
        try:
            parsed_copy = parsed.copy()
            for func in parsed_copy.find_all(exp.Func):
                name = func.sql_name()
                if name == "SUM":
                    func.replace(sqlglot.parse_one(f"AVG({func.this.sql()})"))
                elif name == "AVG":
                    func.replace(sqlglot.parse_one(f"SUM({func.this.sql()})"))
                elif name == "MIN":
                    func.replace(sqlglot.parse_one(f"MAX({func.this.sql()})"))
                elif name == "MAX":
                    func.replace(sqlglot.parse_one(f"MIN({func.this.sql()})"))
            mutations["replace_aggregation"] = parsed_copy.sql()
        except Exception:
            pass

    # 7. Replace literal value
    literals = re.findall(r"'\w+'|\b\d+\b", sql)
    if literals:
        lit = random.choice(literals)
        if lit.isdigit():
            new_lit = str(int(lit) + 1)
        else:
            new_lit = f"'{lit.strip(chr(39))}__mutated'"
        mutations["replace_literal"] = sql.replace(lit, new_lit)

    # 8. Wrong join column
    if " join " in sql.lower() and " on " in sql.lower():
        # Heuristically change the join key
        mutations["wrong_join_column"] = re.sub(
            r"(\bON\b\s+\w+\.)(\w+)(\s*=\s*\w+\.)(\w+)",
            r"\g<1>\g<2>_id\g<3>\g<4>",
            sql,
            flags=re.IGNORECASE
        )

    # 9. Remove cast / add wrong cast
    if "cast(" in sql.lower():
        mutations["remove_cast_or_add_wrong_cast"] = re.sub(
            r"cast\s*\((.*?)\s+as\s+\w+\)", r"\1", sql, flags=re.IGNORECASE
        )
    else:
        # Heuristically cast some column as text
        matches = re.findall(r"\b\w+\.\w+\b", sql)
        if matches:
            col = random.choice(matches)
            mutations["remove_cast_or_add_wrong_cast"] = sql.replace(col, f"CAST({col} AS TEXT)")

    # 10. Replace filter column
    # Heuristically append a suffix to one table/column in where clause
    if "where" in sql.lower():
        where_part = sql.lower().split("where")[1]
        matches = re.findall(r"\b\w+\b", where_part)
        if matches:
            target = random.choice(matches)
            mutations["replace_filter_column"] = sql.replace(target, f"{target}_mut")

    # Clean up results
    valid_mutations = {}
    for k, v in mutations.items():
        v_clean = v.strip().replace("  ", " ")
        if v_clean != sql.strip().replace("  ", " "):
            valid_mutations[k] = v_clean

    return valid_mutations
