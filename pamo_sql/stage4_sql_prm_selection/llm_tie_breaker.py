"""
LLM-based pairwise selector — used as:
  - Version 1 baseline (no training needed)
  - Tie-breaker for trained SQL-PRM
"""

from common.llm_client import call_llm
from stage4_sql_prm_selection.format_pairwise_input import format_pairwise_prompt


class LLMPairwiseSelector:
    """Use LLM API as a pairwise SQL candidate judge."""

    def __init__(self, model=None, temperature=0.0):
        self.model = model
        self.temperature = temperature

    def compare(self, pair):
        """
        Compare two candidates using LLM judge.

        Returns:
            dict with winner ("A"/"B"/"tie"), confidence
        """
        prompt = format_pairwise_prompt(pair)
        response = call_llm(prompt, temperature=self.temperature).strip().upper()

        # Parse response
        if response in ("A", "B", "TIE"):
            winner = response if response != "TIE" else "tie"
        elif "A" in response[:5]:
            winner = "A"
        elif "B" in response[:5]:
            winner = "B"
        else:
            winner = "tie"

        return {
            "winner": winner,
            "confidence": 0.8 if winner != "tie" else 0.5,
            "raw_response": response
        }
