"""
Hospital Service
Loads hospital master list and provides normalization + validation.
"""

import difflib
from pathlib import Path
from typing import Optional


def _load_hospitals() -> list[str]:
    path = Path(__file__).resolve().parent / "data" / "hospitals.txt"
    if not path.exists():
        return []
    return [
        line.strip() for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#") and not line.startswith("---")
    ]


HOSPITAL_MASTER       = _load_hospitals()
HOSPITAL_MASTER_LOWER = [h.lower() for h in HOSPITAL_MASTER]

_KNOWN_CITIES = {
    "hyderabad", "bengaluru", "bangalore", "chennai", "mumbai", "delhi",
    "new delhi", "pune", "kolkata", "ahmedabad", "jaipur", "lucknow",
    "kochi", "vizag", "visakhapatnam", "secunderabad", "coimbatore",
    "madurai", "nagpur", "bhopal", "chandigarh", "thiruvananthapuram",
    "bhubaneswar", "indore", "patna", "guwahati", "mysuru", "mysore",
    "vadodara", "surat", "gachibowli", "jubilee hills", "banjara hills",
    "kondapur", "punjagutta", "hitech city", "ameerpet", "kukatpally",
    "begumpet", "madhapur", "nanakramguda", "manikonda", "miyapur",
    "uppal", "lb nagar", "dilsukhnagar", "malakpet", "abids",
}

_HOSP_KEYWORDS = {
    "hospital", "hospitals", "clinic", "clinics", "centre", "center",
    "medical", "health", "institute", "college", "care", "children",
    "maternity", "nursing", "aiims", "kims", "nims", "pgimer",
    "jipmer", "nimhans", "sgpgi", "mamc", "sims", "hcg", "mgm",
    "aig", "bhu", "kem", "sat", "lnjp", "gtb", "rml",
}


def is_valid_hospital(text: str, spec_service=None) -> bool:
    """Return True if text is a valid hospital name."""
    from app.onboarding_ner.specialization_service import specialization_service as ss
    if spec_service is None:
        spec_service = ss

    t = text.strip().lower()
    if len(t) < 2:
        return False

    _INVALID = {"contact", "mobile", "phone", "email", "number", "call",
                "reach", "address", "mail", "id", "no", "num", "tel",
                "whatsapp", "website", "www", "fax"}
    if t in _INVALID:
        return False
    words = t.split()
    if all(w in _INVALID for w in words):
        return False
    _GEN = {"hospital", "clinic", "centre", "center"}
    if len(words) >= 2 and words[0] in _GEN and words[1] in _INVALID:
        return False

    t_words = set(words)
    _HOSP_QUICK = {"hospital", "hospitals", "clinic", "clinics", "centre",
                   "center", "medical", "health", "institute", "care", "children"}
    if not (t_words & _HOSP_QUICK):
        if spec_service.normalize_strict(text) is not None:
            return False

    if t in _KNOWN_CITIES:
        return False

    if t_words & _HOSP_KEYWORDS:
        non_kw = [w for w in words if w not in _HOSP_KEYWORDS]
        if not non_kw or not all(w in _KNOWN_CITIES for w in non_kw):
            return True

    for m in HOSPITAL_MASTER_LOWER:
        if t == m:
            m_words = set(m.split())
            if m_words & _HOSP_KEYWORDS or (len(t) <= 6 and t.replace(" ", "").isalpha()):
                return True
        if m in t:
            if set(m.split()) & _HOSP_KEYWORDS:
                return True
    return False


def normalize_hospital(name: str) -> str:
    """Normalize hospital name against master. High-threshold fuzzy only."""
    if not name or not name.strip():
        return name
    q = name.strip().lower()
    for i, m in enumerate(HOSPITAL_MASTER_LOWER):
        if q == m:
            return HOSPITAL_MASTER[i]
    hits = [HOSPITAL_MASTER[i] for i, m in enumerate(HOSPITAL_MASTER_LOWER) if q in m]
    if len(hits) == 1:
        return hits[0]
    if len(hits) > 1:
        return min(hits, key=len)
    for i, m in enumerate(HOSPITAL_MASTER_LOWER):
        if m in q:
            return HOSPITAL_MASTER[i]
    close = difflib.get_close_matches(q, HOSPITAL_MASTER_LOWER, n=1, cutoff=0.97)
    if close:
        return HOSPITAL_MASTER[HOSPITAL_MASTER_LOWER.index(close[0])]
    return name.strip().title()
