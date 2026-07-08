"""
Inference with a trained SQL-PRM selector model.
"""

import torch
from stage4_sql_prm_selection.format_pairwise_input import format_pairwise_prompt


class SQLPRMSelector:
    """Trained pairwise SQL reward model for candidate comparison."""

    def __init__(self, model_path):
        from transformers import AutoTokenizer, AutoModelForSequenceClassification

        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_path)
        self.model.eval()
        self.id2label = self.model.config.id2label

    @torch.no_grad()
    def compare(self, pair):
        """
        Compare two candidates and return winner prediction.

        Args:
            pair: dict with question, evidence, context, candidate_a, candidate_b

        Returns:
            dict with winner ("A"/"B"/"tie"), confidence, probs
        """
        text = format_pairwise_prompt(pair)
        inputs = self.tokenizer(
            text, return_tensors="pt", truncation=True, max_length=2048
        )
        logits = self.model(**inputs).logits[0]
        probs = torch.softmax(logits, dim=-1).tolist()
        pred_id = int(torch.argmax(logits).item())
        label = self.id2label[pred_id]
        confidence = max(probs)

        return {
            "winner": label,
            "confidence": confidence,
            "probs": {self.id2label[i]: round(p, 4) for i, p in enumerate(probs)}
        }
