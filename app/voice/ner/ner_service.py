"""
NER Service
Loads the custom-trained spaCy model and runs entity extraction.
Returns raw spans â€” no normalization, no validation.
"""

import spacy
from pathlib import Path
from typing import Optional

_MODEL_PATH = Path(__file__).resolve().parent / "models" / "model-best"
_nlp: Optional[spacy.language.Language] = None


def _get_nlp():
    global _nlp
    if _nlp is None:
        if not _MODEL_PATH.exists():
            raise RuntimeError(
                f"NER model not found at {_MODEL_PATH}. "
                "Copy models/model-best/ into app/onboarding_ner/models/"
            )
        _nlp = spacy.load(str(_MODEL_PATH))
    return _nlp


def extract_raw(text: str) -> dict[str, list[dict]]:
    """
    Run spaCy NER on text. Returns raw unvalidated spans.

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

