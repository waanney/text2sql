import json
from pathlib import Path
from stage2_generation.generator_reasoning import generate_reasoning_sql
from stage2_generation.generator_icl import generate_icl_sql
from stage2_generation.generator_metadata_constrained import generate_metadata_constrained_sql
from stage2_generation.generator_evidence_focused import generate_evidence_focused_sql
from stage2_generation.generator_join_focused import generate_join_focused_sql
from stage2_generation.generator_simple import generate_simple_sql


def generate_all_candidates(context_path, ddl_schema, light_schema, output_path, config=None):
    with open(context_path, "r", encoding="utf-8") as f:
        context = json.load(f)

    # Wire ablation config/stages:
    stages = {}
    generation = {}
    if config:
        stages = config.get("stages", {})
        generation = config.get("generation", {})

    use_reasoning = stages.get("use_reasoning_generator", True)
    use_icl = stages.get("use_icl_generator", True)
    use_metadata_constrained = stages.get("use_metadata_constrained_generator", True)
    use_evidence_focused = stages.get("use_evidence_focused_generator", True)
    use_join_focused = stages.get("use_join_focused_generator", True)
    use_simple = stages.get("use_simple_generator", True)

    reasoning_n = generation.get("reasoning_n", 3)
    icl_n = generation.get("icl_n", 3)
    metadata_constrained_n = generation.get("metadata_constrained_n", 2)
    evidence_focused_n = generation.get("evidence_focused_n", 3)
    join_focused_n = generation.get("join_focused_n", 3)
    simple_n = generation.get("simple_n", 1)

    candidates = []
    if use_reasoning and reasoning_n > 0:
        candidates += generate_reasoning_sql(context, ddl_schema, n=reasoning_n)
    if use_icl and icl_n > 0:
        candidates += generate_icl_sql(context, light_schema, n=icl_n)
    if use_metadata_constrained and metadata_constrained_n > 0:
        candidates += generate_metadata_constrained_sql(context, ddl_schema, n=metadata_constrained_n)
    if use_evidence_focused and evidence_focused_n > 0:
        candidates += generate_evidence_focused_sql(context, ddl_schema, n=evidence_focused_n)
    if use_join_focused and join_focused_n > 0:
        candidates += generate_join_focused_sql(context, ddl_schema, n=join_focused_n)
    if use_simple and simple_n > 0:
        candidates += generate_simple_sql(context, light_schema, n=simple_n)

    from common.sql_utils import clean_sql

    for idx, c in enumerate(candidates):
        c["candidate_id"] = f'{context["question_id"]}_cand_{idx}'
        c["question_id"] = context["question_id"]
        c["db_id"] = context["db_id"]
        c["sql"] = clean_sql(c.get("sql", ""))

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(candidates, f, ensure_ascii=False, indent=2)

    return candidates
