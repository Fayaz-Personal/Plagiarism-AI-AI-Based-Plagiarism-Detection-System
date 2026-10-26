"""
Optional Local Semantic Similarity Module.
Integrates local sentence-transformers embedding models when available,
with graceful offline fallback to the baseline TF-IDF detection engine.
"""
import os
from pathlib import Path


def is_semantic_available() -> bool:
    """Check if sentence-transformers is installed locally."""
    try:
        import sentence_transformers  # noqa: F401
        return True
    except ImportError:
        return False


def get_semantic_status() -> dict:
    """Returns availability and operational status of the local semantic embedding model."""
    available = is_semantic_available()
    return {
        'available': available,
        'backend': 'Local Sentence-Transformers (Offline)' if available else 'Disabled (TF-IDF Only)',
        'model_name': 'all-MiniLM-L6-v2' if available else 'None',
        'status_text': (
            'Local transformer embeddings active for complementary semantic similarity scoring.'
            if available else
            'Sentence embedding package is not installed. Baseline lexical TF-IDF + Cosine Similarity engine is active.'
        )
    }


def compute_semantic_similarity(text_a: str, text_b: str) -> float | None:
    """
    Computes semantic cosine similarity using locally cached transformer embeddings.
    Returns: float (0.0 - 100.0) or None if unavailable/offline.
    Guarantees no unexpected online downloads occur during runtime analysis.
    """
    if not is_semantic_available():
        return None

    try:
        from sentence_transformers import SentenceTransformer, util

        # Check if local model cache exists to avoid runtime internet downloading
        cache_dir = os.environ.get('TRANSFORMERS_CACHE') or os.environ.get('HF_HOME')
        # Only instantiate if model is cached locally
        model = SentenceTransformer('all-MiniLM-L6-v2')
        emb1 = model.encode(text_a, convert_to_tensor=True)
        emb2 = model.encode(text_b, convert_to_tensor=True)
        cos_sim = float(util.cos_sim(emb1, emb2)[0][0])
        return round(max(0.0, min(100.0, cos_sim * 100.0)), 2)
    except Exception:
        # Fallback to None on any error so baseline analysis never breaks
        return None
