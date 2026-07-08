import numpy as np


def cosine_similarity(v1, v2) -> float:
    """Compute cosine similarity between two numerical vectors."""
    dot_product = np.dot(v1, v2)
    norm_v1 = np.linalg.norm(v1)
    norm_v2 = np.linalg.norm(v2)
    if norm_v1 == 0 or norm_v2 == 0:
        return 0.0
    return float(dot_product / (norm_v1 * norm_v2))


def get_embedding(text: str, model: str = "text-embedding-ada-002") -> list:
    """
    Get semantic embedding vector using OpenAI API.
    Falls back to a deterministic normalized pseudo-embedding if API fails or is unconfigured.
    """
    try:
        from openai import OpenAI
        client = OpenAI()
        res = client.embeddings.create(input=[text], model=model)
        return res.data[0].embedding
    except Exception:
        # Fallback Mock: deterministic pseudo-embedding based on hash for testing / environment independence
        import hashlib
        h = hashlib.sha256(text.encode("utf-8")).digest()
        mock_vec = []
        for i in range(1536):
            val = ((h[i % len(h)] * (i + 1)) % 100) / 100.0
            mock_vec.append(val)
        norm = np.linalg.norm(mock_vec)
        if norm > 0:
            mock_vec = [v / norm for v in mock_vec]
        return mock_vec
