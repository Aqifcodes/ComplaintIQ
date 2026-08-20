import logging

from sentence_transformers import SentenceTransformer, util

from app.database import add_or_increment_pending_category, get_pending_categories

logger = logging.getLogger(__name__)

MODEL_NAME = "all-MiniLM-L6-v2"
PENDING_CATEGORY_SIMILARITY_THRESHOLD = 0.85

_model = None


def _get_model():
    global _model
    if _model is None:
        try:
            _model = SentenceTransformer(MODEL_NAME)
        except Exception as e:
            logger.exception("Failed to load sentence-transformers model '%s': %s", MODEL_NAME, e)
            raise
    return _model


def resolve_pending_category(proposed_category: str) -> str:
    """Resolve the best pending category for a proposed Gemini category.

    If an existing pending category is semantically similar enough, increment that
    category instead of creating a new one.

    Returns the pending category name that should receive the complaint count.
    """
    if not proposed_category or not proposed_category.strip():
        raise ValueError("proposed_category must be a non-empty string")

    proposed = proposed_category.strip()
    pending_rows = get_pending_categories()

    if not pending_rows:
        add_or_increment_pending_category(proposed)
        return proposed

    model = _get_model()
    texts = [proposed] + [row["category_name"] for row in pending_rows]

    embeddings = model.encode(texts, convert_to_tensor=True, show_progress_bar=False, normalize_embeddings=True)
    proposed_embedding = embeddings[0]
    pending_embeddings = embeddings[1:]

    if pending_embeddings.shape[0] == 0:
        add_or_increment_pending_category(proposed)
        return proposed

    similarities = util.cos_sim(proposed_embedding, pending_embeddings)[0]
    best_idx = int(similarities.argmax().item())
    best_similarity = float(similarities[best_idx].item())
    best_category = pending_rows[best_idx]["category_name"]

    if best_similarity >= PENDING_CATEGORY_SIMILARITY_THRESHOLD:
        add_or_increment_pending_category(best_category)
        return best_category

    add_or_increment_pending_category(proposed)
    return proposed
