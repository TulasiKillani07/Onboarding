"""
Normalization Service
Applies normalization rules to validated entities.
  DOCTOR_NAME   â€” strip title (Dr., Prof., etc.)
  HOSPITAL      â€” exact/contains/high-fuzzy match against master
  SPECIALIZATION â€” exact/alias match against synonym map
"""

import re
from app.voice.ner.specialization_service import specialization_service
from app.voice.ner.hospital_service import normalize_hospital

TITLE_RE = re.compile(
    r"^(Dr\.?\s+|Prof\.?\s+|Professor\s+|Mr\.?\s+|Mrs\.?\s+|Ms\.?\s+|"
    r"Sir\s+|Doctor\s+|Shri\s+|Smt\.?\s+)",
    re.IGNORECASE,
)

SPEC_CONTEXT_RE = re.compile(
    r"\b(i\s+am|i'm|i\s+am\s+a|i'm\s+a|i\s+am\s+an|i'm\s+an"
    r"|working\s+as|work\s+as|practice\s+as|specialist\s+in"
    r"|speciali[sz]e\s+in|speciali[sz]ation\s+is|field\s+is"
    r"|trained\s+as|qualified\s+as|my\s+specialty|my\s+specialization)\b",
    re.IGNORECASE,
)


def strip_title(name: str) -> tuple[str, int]:
    """
    Remove leading title from name.
    Returns (clean_name, chars_stripped).
    """
    stripped = TITLE_RE.sub("", name).strip()
    chars_stripped = len(name) - len(name.lstrip()) + (len(name.lstrip()) - len(stripped))
    return stripped, len(name) - len(stripped)


def in_spec_context(span_text: str, full_text: str) -> bool:
    """Return True if span appears after a specialization context phrase."""
    idx = full_text.lower().find(span_text.lower())
    if idx == -1:
        return False
    preceding = full_text.lower()[max(0, idx - 60): idx]
    return bool(SPEC_CONTEXT_RE.search(preceding))


def normalize_doctor_name(span: dict, full_text: str) -> tuple[dict | None, dict | None]:
    """
    Normalize a DOCTOR_NAME span.
    Returns (name_span_or_None, spec_span_or_None).
    If the name is actually a specialization in context, returns (None, spec_span).
    """
    original = span["text"]
    name, _ = strip_title(original)

    # Recalculate start
    start = span["start"]
    if name != original:
        off = original.find(name)
        if off < 0:
            off = original.lower().find(name.lower())
        if off >= 0:
            start = span["start"] + off

    # Reclassify if alias + context (no fuzzy)
    alias = specialization_service.normalize_strict(name)
    if alias and in_spec_context(span["text"], full_text):
        return None, {"text": alias, "start": start, "end": span["end"]}

    return {"text": name, "start": start, "end": span["end"]}, None


def normalize_spec(raw_text: str) -> str | None:
    """Normalize specialization text. Returns canonical name or None if invalid."""
    return specialization_service.normalize_strict(raw_text)


def normalize_hosp(span: dict) -> dict:
    """Normalize hospital span text against master list."""
    norm = normalize_hospital(span["text"])
    return {"text": norm, "start": span["start"], "end": span["end"]}

