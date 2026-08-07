"""
Pattern Extractor
Finds specialization phrases using grammatical context patterns.
e.g. "I am skin specialist", "working as heart doctor"
This is NOT NER. Returns only candidates that exist in the spec master.
"""

import re
from app.voice.ner.specialization_service import specialization_service

SPEC_PATTERNS = [
    re.compile(r"\bi(?:'m| am)\s+(?:a|an|the)?\s*([a-z][a-z\s]{2,35}?)(?:\.|,|\s+at\s|\s+in\s|\s+and\s|\s+my\s|\s+work|\s+from|\s+based|$)", re.IGNORECASE),
    re.compile(r"\b(?:working|work|practice|practicing|practise|trained|qualified)\s+as\s+(?:a|an)?\s*([a-z][a-z\s]{2,35}?)(?:\.|,|\s+at\s|\s+in\s|\s+and\s|\s+my\s|\s+from|\s+based|$)", re.IGNORECASE),
    re.compile(r"\bmy\s+(?:speciali[sz]ation|specialty|speciality|field|area|background)\s+is\s+(?:in\s+)?([a-z][a-z\s]{2,35}?)(?:\.|,|\s+at\s|\s+and\s|\s+my\s|\s+from\s|$)", re.IGNORECASE),
    re.compile(r"\bi\s+speciali[sz]e\s+in\s+([a-z][a-z\s]{2,35}?)(?:\.|,|\s+at\s|\s+and\s|\s+my\s|\s+from\s|$)", re.IGNORECASE),
    re.compile(r"(?<!hospital\s)(?<!clinic\s)\bspecialist\s+in\s+([a-z][a-z\s]{2,35}?)(?:\.|,|\s+at\s|\s+and\s|$)", re.IGNORECASE),
]

_NEGATIVE_SUFFIX = re.compile(
    r"\b(hospital|hospitals|clinic|clinics|centre|center|institute|department)\b",
    re.IGNORECASE,
)
_NAME_PREFIX = re.compile(r"^(dr\.?\s|doctor\s|prof\.?\s|mr\.?\s|mrs\.?\s|ms\.?\s)", re.IGNORECASE)


def extract_specialization_patterns(text: str) -> list[dict]:
    """
    Extract specialization candidates from grammatical patterns.
    Only returns candidates that exist in the specialization master.
    """
    candidates = []
    seen = set()

    for pattern in SPEC_PATTERNS:
        for m in pattern.finditer(text):
            candidate = m.group(1).strip().rstrip(".,;:")
            if _NAME_PREFIX.match(candidate):
                continue
            if len(candidate) < 3 or len(candidate) > 60:
                continue
            if any(c.isdigit() for c in candidate):
                continue
            end_pos = text.lower().find(candidate.lower(), m.start())
            if end_pos >= 0:
                suffix = text[end_pos + len(candidate): end_pos + len(candidate) + 30]
                if _NEGATIVE_SUFFIX.search(suffix.split(".")[0]):
                    continue
            if not specialization_service.normalize_strict(candidate):
                continue
            key = candidate.lower().strip()
            if key not in seen:
                seen.add(key)
                candidates.append({
                    "text":  candidate,
                    "start": m.start(1),
                    "end":   m.start(1) + len(candidate),
                })

    return candidates

