import json


def format_pairwise_prompt(pair):
    """Format a pairwise comparison into a text prompt for LLM or model input."""
    return f"""You are a Text-to-SQL candidate selector.
Your task is to compare two SQL candidates for the same question.
Choose which candidate better answers the question.

Question:
{pair['question']}

Evidence / Oracle Knowledge:
{pair.get('evidence') or ''}

Grounded context:
{json_dumps(pair['context'])}

Candidate A SQL:
{pair['candidate_a']['sql']}

Candidate A execution summary:
{json_dumps(pair['candidate_a']['execution'])}

Candidate B SQL:
{pair['candidate_b']['sql']}

Candidate B execution summary:
{json_dumps(pair['candidate_b']['execution'])}

Decision rules:
1. Prefer SQL that satisfies the question intent.
2. Prefer SQL that correctly uses evidence/oracle constraints.
3. Prefer SQL that maps literals to the matched database columns.
4. Prefer SQL that uses verified join paths.
5. Prefer SQL whose execution result shape matches the question.
6. Penalize syntax errors, empty suspicious results, wrong aggregation, and wrong joins.
7. If both are equivalent, answer tie.

Answer only one token: A, B, or tie.""".strip()


def format_pair_for_training(pair):
    """Format a labeled pair into a training example dict."""
    text = format_pairwise_prompt(pair)
    return {
        "text": text,
        "winner": pair["winner"],
        "question_id": pair["question_id"]
    }


def json_dumps(obj):
    return json.dumps(obj, ensure_ascii=False, indent=2)
