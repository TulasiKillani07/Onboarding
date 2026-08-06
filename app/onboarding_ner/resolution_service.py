"""
Resolution Service
Collapses multi-value entity lists to exactly one value (or null).
  0 values → null
  1 value  → return it
  2+ values → score by context → winner or null if tied
"""

import re
from typing import Optional

WINDOW = 80

_NAME_POS = [(r"\bmy\s+name\s+is\b", 100), (r"\bi\s*'m\b", 100), (r"\bi\s+am\b", 100),
             (r"\bthis\s+is\b", 80), (r"\bmyself\b", 80), (r"\bspeaking\b", 60), (r"\bdr\.?\s+", 20)]
_NAME_NEG = [(r"\bcolleague\b", -50), (r"\breferred\s+by\b", -50), (r"\bhe\s+is\b", -30), (r"\bshe\s+is\b", -30)]

_HOSP_POS = [(r"\bworking\s+at\b", 100), (r"\bwork\s+at\b", 100), (r"\bcurrently\s+at\b", 100),
             (r"\bpractice\s+at\b", 90), (r"\bposted\s+at\b", 90), (r"\bjoined\b", 70)]
_HOSP_NEG = [(r"\bpreviously\b", -60), (r"\bformerly\b", -60), (r"\bused\s+to\b", -60)]

_SPEC_POS = [(r"\bi\s*'m\s+a\b", 100), (r"\bi\s+am\s+a\b", 100),
             (r"\bi\s+speciali[sz]e\s+in\b", 100), (r"\bworking\s+as\s+a\b", 90)]
_SPEC_NEG = [(r"\bpreviously\b", -60), (r"\bused\s+to\b", -60)]

_PHONE_POS = [(r"\bmy\s+(?:phone|mobile|number|contact|cell)\b", 100), (r"\bcall\s+me\b", 80)]
_PHONE_NEG = [(r"\bhospital\s+(?:number|phone)\b", -60), (r"\breception\b", -50)]

_EMAIL_POS = [(r"\bmy\s+email\b", 100), (r"\bmy\s+mail\b", 90)]
_EMAIL_NEG = [(r"\bhospital\s+email\b", -60), (r"\boffice\s+email\b", -50)]


def _score(span_text: str, full_text: str, pos: list, neg: list) -> int:
    tl = full_text.lower()
    sl = span_text.strip().lower()
    idx = tl.find(sl)
    if idx == -1:
        return 0
    ctx = tl[max(0, idx - WINDOW): idx] + " " + tl[idx + len(sl): idx + len(sl) + WINDOW]
    score = 0
    for p, w in pos:
        if re.search(p, ctx, re.IGNORECASE):
            score += w
    for p, w in neg:
        if re.search(p, ctx, re.IGNORECASE):
            score += w
    return score


def _resolve(candidates: list[dict], full_text: str, pos: list, neg: list,
             allow_tie: bool = False) -> Optional[str]:
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]["text"]
    scored = sorted([((_score(c["text"], full_text, pos, neg)), c["text"]) for c in candidates], reverse=True)
    best, second = scored[0][0], scored[1][0] if len(scored) > 1 else -9999
    if best == second and not allow_tie:
        return None
    if best <= 0 and not allow_tie:
        return None
    return scored[0][1]


def resolve(entities: dict, full_text: str) -> dict:
    """Collapse all entity lists to single values."""
    # Hospital: onboarding context — if tied, take last mentioned
    hosp_candidates = entities.get("HOSPITAL", [])
    if len(hosp_candidates) > 1:
        scored = [(_score(c["text"], full_text, _HOSP_POS, _HOSP_NEG), c["text"]) for c in hosp_candidates]
        best_score = max(s for s, _ in scored)
        best_names = [n for s, n in scored if s == best_score]
        if len(best_names) == 1:
            hospital = best_names[0]
        else:
            tl = full_text.lower()
            hospital = max(best_names, key=lambda n: tl.rfind(n.lower()))
    else:
        hospital = hosp_candidates[0]["text"] if hosp_candidates else None

    # Specialization: null if tied
    spec_candidates = entities.get("SPECIALIZATION", [])
    if len(spec_candidates) > 1:
        scored = sorted([(_score(c["text"], full_text, _SPEC_POS, _SPEC_NEG), c["text"]) for c in spec_candidates], reverse=True)
        specialization = scored[0][1] if scored[0][0] > scored[1][0] else None
    else:
        specialization = spec_candidates[0]["text"] if spec_candidates else None

    return {
        "doctor_name":    _resolve(entities.get("DOCTOR_NAME", []), full_text, _NAME_POS, _NAME_NEG),
        "hospital":       hospital,
        "specialization": specialization,
        "phone":          _resolve(entities.get("PHONE", []), full_text, _PHONE_POS, _PHONE_NEG, allow_tie=False),
        "email":          _resolve(entities.get("EMAIL", []), full_text, _EMAIL_POS, _EMAIL_NEG, allow_tie=False),
    }
