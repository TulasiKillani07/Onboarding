"""
Validation Service
Rejects garbage entities before normalization.
Rules:
  DOCTOR_NAME  — reject contact/comm words, digits, known invalid tokens
  HOSPITAL     — delegated to hospital_service.is_valid_hospital()
  SPECIALIZATION — must exist in specialization master (strict alias match)
"""

from app.onboarding_ner.specialization_service import specialization_service
from app.onboarding_ner.hospital_service import is_valid_hospital

_INVALID_NAME = {
    "contact", "mobile", "phone", "email", "number", "call",
    "hospital", "hospitals", "clinic", "clinics", "centre", "center",
    "specialist", "doctor", "surgeon", "physician", "therapist",
    "department", "medicine", "medical", "health", "healthcare",
    "reach", "address", "mail", "id", "no", "num", "tel",
    "whatsapp", "website", "www", "fax",
}

_INVALID_SPEC = {
    "contact", "mobile", "phone", "email", "number", "call",
    "reach", "address", "mail", "id", "no", "num", "tel",
    "whatsapp", "telegram", "fax", "website", "www",
}


def is_valid_doctor_name(text: str) -> bool:
    t = text.strip().lower()
    if len(t) < 2 or any(c.isdigit() for c in t):
        return False
    if t in _INVALID_NAME:
        return False
    words = t.split()
    return not all(w in _INVALID_NAME for w in words)


def is_valid_specialization(text: str) -> bool:
    t = text.strip().lower()
    if t in _INVALID_SPEC:
        return False
    return specialization_service.normalize_strict(text) is not None
