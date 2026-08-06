"""
OnboardingNER Pipeline
Single public entry point for the entire NER extraction pipeline.

Usage:
    from app.onboarding_ner import OnboardingNER
    result = OnboardingNER.process(transcript)

Pipeline stages:
    1. Regex          → PHONE, EMAIL
    2. NER + Validate → DOCTOR_NAME, HOSPITAL, SPECIALIZATION
    3. Pattern Extract → additional specialization phrases
    4. Normalization  → strip title | hospital lookup | spec alias
    5. Resolution     → 1 value per field or null

This module knows nothing about Sarvam or audio.
Input: plain text string
Output: dict with doctor_name, hospital, specialization, phone, email
"""

from typing import Optional
from app.onboarding_ner.regex_service       import extract_phones, extract_emails
from app.onboarding_ner.ner_service         import extract_raw
from app.onboarding_ner.validation_service  import is_valid_doctor_name, is_valid_hospital, is_valid_specialization
from app.onboarding_ner.pattern_extractor   import extract_specialization_patterns
from app.onboarding_ner.normalization_service import normalize_doctor_name, normalize_hosp, normalize_spec
from app.onboarding_ner.resolution_service  import resolve
from app.onboarding_ner.specialization_service import specialization_service

# Normalization log — tracks every correction for retraining signal
_normalization_log: list[dict] = []

def _log(category: str, original: str, normalized: str):
    if original != normalized:
        _normalization_log.append({"category": category, "original": original, "normalized": normalized})

def get_normalization_log() -> list[dict]:
    return _normalization_log[-200:]


class OnboardingNER:
    """
    Orchestrates the full doctor onboarding NER pipeline.
    Stateless — all methods are static.
    """

    @staticmethod
    def process(text: str) -> dict:
        """
        Extract doctor registration data from plain text.

        Args:
            text: Transcript or typed text from the doctor

        Returns:
            {
                "doctor_name": str | None,
                "hospital": str | None,
                "specialization": str | None,
                "phone": str | None,
                "email": str | None,
                "entities": dict   # raw multi-value for debugging
            }
        """
        entities = OnboardingNER._extract(text)
        resolved = resolve(entities, text)
        return {**resolved, "entities": entities}

    @staticmethod
    def _extract(text: str) -> dict:
        """Run stages 1-4 and return multi-value entity dict."""

        # Stage 1: Regex
        phones = extract_phones(text)
        emails = extract_emails(text)

        # Stage 2: NER + validation
        raw = extract_raw(text)
        ner_names = [s for s in raw["DOCTOR_NAME"] if is_valid_doctor_name(s["text"])]
        ner_hosps = [s for s in raw["HOSPITAL"]     if is_valid_hospital(s["text"])]
        ner_specs = [s for s in raw["SPECIALIZATION"] if is_valid_specialization(s["text"])]

        for s in raw["DOCTOR_NAME"]:
            if not is_valid_doctor_name(s["text"]):
                _log("DOCTOR_NAME.rejected", s["text"], "INVALID")
        for s in raw["HOSPITAL"]:
            if not is_valid_hospital(s["text"]):
                _log("HOSPITAL.rejected", s["text"], "INVALID")
        for s in raw["SPECIALIZATION"]:
            if not is_valid_specialization(s["text"]):
                _log("SPECIALIZATION.rejected", s["text"], "INVALID")

        # Stage 3: Pattern extractor
        ner_spec_lower = {s["text"].lower() for s in ner_specs}
        for ps in extract_specialization_patterns(text):
            if ps["text"].lower() not in ner_spec_lower and is_valid_specialization(ps["text"]):
                ner_specs.append(ps)
                ner_spec_lower.add(ps["text"].lower())
                _log("PATTERN.spec_found", ps["text"], ps["text"])

        # Stage 4: Normalization
        final_names, final_hosps, final_specs = [], [], []
        seen_specs: set[str] = set()

        def _add_spec(raw_text: str, start: int, end: int):
            if not is_valid_specialization(raw_text):
                return
            norm = normalize_spec(raw_text) or raw_text
            _log("SPECIALIZATION", raw_text, norm)
            key = norm.lower()
            if key not in seen_specs:
                seen_specs.add(key)
                final_specs.append({"text": norm, "start": start, "end": end})

        # DOCTOR_NAME: strip title, reclassify if alias + context
        for span in ner_names:
            name_span, spec_span = normalize_doctor_name(span, text)
            if spec_span:
                _log("DOCTOR_NAME->SPECIALIZATION", span["text"], spec_span["text"])
                _add_spec(spec_span["text"], spec_span["start"], spec_span["end"])
            elif name_span:
                _log("DOCTOR_NAME.strip_title", span["text"], name_span["text"])
                final_names.append(name_span)

        # HOSPITAL: exact/contains/high-fuzzy
        for span in ner_hosps:
            norm_span = normalize_hosp(span)
            _log("HOSPITAL", span["text"], norm_span["text"])
            final_hosps.append(norm_span)

        # SPECIALIZATION: alias only, deduped
        for span in ner_specs:
            _add_spec(span["text"], span["start"], span["end"])

        return {
            "DOCTOR_NAME":    final_names,
            "HOSPITAL":       final_hosps,
            "SPECIALIZATION": final_specs,
            "PHONE":          phones,
            "EMAIL":          emails,
        }
