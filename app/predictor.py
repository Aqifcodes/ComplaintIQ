from pathlib import Path
import logging

from joblib import load
from app.gemini_service import (
    get_current_official_categories,
    gemini_classify_complaint,
    gemini_classify_priority,
)
from app.semantic_similarity import resolve_pending_category

logger = logging.getLogger(__name__)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = PROJECT_ROOT / "trained_models"
VECT_PATH = MODELS_DIR / "tfidf_vectorizer.pkl"
CAT_MODEL_PATH = MODELS_DIR / "category_model.pkl"
PRIO_MODEL_PATH = MODELS_DIR / "priority_model.pkl"


# Load models at import time with basic error handling
_vectorizer = None
_cat_model = None
_prio_model = None

def _load_models():
    global _vectorizer, _cat_model, _prio_model
    try:
        if VECT_PATH.exists():
            _vectorizer = load(VECT_PATH)
        else:
            logger.error("TF-IDF vectorizer not found at %s", VECT_PATH)
    except Exception as e:
        logger.exception("Failed to load TF-IDF vectorizer: %s", e)

    try:
        if CAT_MODEL_PATH.exists():
            _cat_model = load(CAT_MODEL_PATH)
        else:
            logger.error("Category model not found at %s", CAT_MODEL_PATH)
    except Exception as e:
        logger.exception("Failed to load category model: %s", e)

    try:
        if PRIO_MODEL_PATH.exists():
            _prio_model = load(PRIO_MODEL_PATH)
        else:
            logger.error("Priority model not found at %s", PRIO_MODEL_PATH)
    except Exception as e:
        logger.exception("Failed to load priority model: %s", e)


# Attempt initial load
_load_models()

CATEGORY_CONFIDENCE_THRESHOLD = 0.60
PRIORITY_CONFIDENCE_THRESHOLD = 0.60


def predict_complaint(text: str):
    """Predict complaint category and priority for the provided text.

    Returns a dictionary with keys: category, category_confidence,
    priority, priority_confidence, and handled_by. Confidence values are Python floats.
    Raises RuntimeError if required models are not available.
    """
    if not text:
        raise ValueError("Text must be a non-empty string")

    if _vectorizer is None or _cat_model is None or _prio_model is None:
        # Try a reload once more before failing
        _load_models()
        if _vectorizer is None or _cat_model is None or _prio_model is None:
            raise RuntimeError("One or more ML artifacts could not be loaded")

    try:
        X = _vectorizer.transform([text])

        # Category prediction and confidence
        cat_pred = _cat_model.predict(X)[0]
        try:
            cat_probas = _cat_model.predict_proba(X)[0]
            # Use the max probability as confidence
            cat_conf = float(max(cat_probas))
        except Exception:
            cat_conf = 0.0

        cat_source = "Random Forest"

        print(f"[ML] Predicted Category: {cat_pred}")
        print(f"[ML] Category Confidence: {cat_conf:.2f}")
        print(f"[ML] Threshold: {CATEGORY_CONFIDENCE_THRESHOLD:.2f}")

        if cat_conf >= CATEGORY_CONFIDENCE_THRESHOLD:
            print("[ML] Decision: Using Random Forest")
            cat_source = "Random Forest"
        else:
            print("[ML] Decision: Low confidence -> Calling Gemini fallback")
            try:
                official_categories = get_current_official_categories()
                gemini_result = gemini_classify_complaint(text, official_categories)
                cat_pred = gemini_result["category"]
                if gemini_result.get("decision") == "new":
                    cat_pred = resolve_pending_category(cat_pred)
                cat_source = "Gemini"
                print(f"[Gemini] Fallback Result: {cat_pred}")
            except Exception as gemini_error:
                cat_source = "Random Forest"
                logger.exception("Gemini fallback failed, using RF category: %s", gemini_error)
                print("[Gemini] Fallback Failed -> Keeping Random Forest prediction")

        # Priority prediction and confidence
        prio_pred = _prio_model.predict(X)[0]
        prio_source = "Random Forest"
        try:
            prio_probas = _prio_model.predict_proba(X)[0]
            prio_conf = float(max(prio_probas))
        except Exception:
            prio_conf = 0.0

        print(f"[ML] Predicted Priority: {prio_pred}")
        print(f"[ML] Priority Confidence: {prio_conf:.2f}")
        print(f"[ML] Priority Threshold: {PRIORITY_CONFIDENCE_THRESHOLD:.2f}")

        if prio_conf >= PRIORITY_CONFIDENCE_THRESHOLD:
            print("[ML] Decision: Using Random Forest")
        else:
            print("[ML] Decision: Low confidence -> Calling Gemini fallback")
            try:
                gemini_priority_result = gemini_classify_priority(text)
                prio_pred = gemini_priority_result["priority"]
                prio_source = "Gemini"
                print(f"[Gemini] Priority Fallback Result: {prio_pred}")
            except Exception as gemini_error:
                prio_source = "Random Forest"
                logger.exception("Gemini priority fallback failed, using RF priority: %s", gemini_error)
                print("[Gemini] Priority Fallback Failed -> Keeping Random Forest prediction")

        return {
            "category": str(cat_pred),
            "category_confidence": float(cat_conf),
            "priority": str(prio_pred),
            "priority_confidence": float(prio_conf),
            "category_source": cat_source,
            "priority_source": prio_source,
            "handled_by": cat_source,
        }
    except Exception as e:
        logger.exception("Prediction failed: %s", e)
        raise
