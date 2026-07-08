import pickle
import os

def rule_based_rank_columns(feature_df):
    df = feature_df.copy()

    df["relevance_score"] = (
        0.30 * df["semantic_score"]
        + 0.25 * df["literal_match"]
        + 0.20 * df["output_match"]
        + 0.15 * df["filter_match"]
        + 0.10 * df["query_log_support"]
    )

    return df.sort_values("relevance_score", ascending=False)


class TabularSchemaRanker:
    def __init__(self, model=None):
        self.model = model
        self.feature_cols = [
            "semantic_score",
            "literal_match",
            "output_match",
            "filter_match",
            "is_id_like",
            "is_date_like",
            "is_numeric_like",
            "null_ratio",
            "distinct_count",
            "query_log_support",
        ]

    def fit(self, X_df, y):
        """Fit the model using scikit-learn LogisticRegression or similar."""
        if self.model is None:
            try:
                from sklearn.linear_model import LogisticRegression
                self.model = LogisticRegression()
            except ImportError:
                raise ImportError("scikit-learn is required to train the TabularSchemaRanker model.")
        self.model.fit(X_df[self.feature_cols], y)
        return self

    def predict(self, feature_df):
        if self.model is None:
            # Fallback to rule-based scoring if model is not trained
            print("[TabularSchemaRanker] Model is not loaded/trained. Falling back to rule-based relevance.")
            df = feature_df.copy()
            df["relevance_score"] = (
                0.30 * df["semantic_score"]
                + 0.25 * df["literal_match"]
                + 0.20 * df["output_match"]
                + 0.15 * df["filter_match"]
                + 0.10 * df["query_log_support"]
            )
            return df.sort_values("relevance_score", ascending=False)

        scores = self.model.predict_proba(feature_df[self.feature_cols])[:, 1]
        output = feature_df.copy()
        output["relevance_score"] = scores
        return output.sort_values("relevance_score", ascending=False)

    def save(self, filepath: str):
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "wb") as f:
            pickle.dump(self.model, f)

    @classmethod
    def load(cls, filepath: str):
        with open(filepath, "rb") as f:
            model = pickle.load(f)
        return cls(model=model)
