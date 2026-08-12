"""
NER Service
Loads the custom-trained spaCy model and runs entity extraction.
Returns raw spans - no normalization, no validation.

Model is loaded once at app startup via load_model().
Inference is CPU-bound so callers should use asyncio.to_thread().
"""

import spacy
from pathlib import Path
from typing import Optional
from app.utils.logger import get_dobo_logger

logger = get_dobo_logger(__name__)

_MODEL_PATH = Path(__file__).resolve().parent / "models" / "model-best"
_nlp: Optional[spacy.language.Language] = None


def load_model():
    """Load the spaCy model into memory. Call once at app startup."""
    global _nlp
    if _nlp is not None:
        return
    if not _MODEL_PATH.exists():
        raise RuntimeError(
            f"NER model not found at {_MODEL_PATH}. "
            "Copy models/model-best/ into app/voice/ner/models/"
        )
    _nlp = spacy.load(str(_MODEL_PATH))
    logger.info(f"spaCy model loaded from {_MODEL_PATH}")


def _get_nlp():
    global _nlp
    if _nlp is None:
        load_model()
    return _nlp


def extract_raw(text: str) -> dict[str, list[dict]]:
    """
    Run spaCy NER on text. Returns raw unvalidated spans.
    CPU-bound - wrap in asyncio.to_thread() when calling from async context.

    Returns:
        {"DOCTOR_NAME": [...], "HOSPITAL": [...], "SPECIALIZATION": [...]}
    """
    nlp = _get_nlp()
    doc = nlp(text)
    result = {"DOCTOR_NAME": [], "HOSPITAL": [], "SPECIALIZATION": []}
    for ent in doc.ents:
        if ent.label_ in result:
            result[ent.label_].append({
                "text":  ent.text,
                "start": ent.start_char,
                "end":   ent.end_char,
            })
    return result
