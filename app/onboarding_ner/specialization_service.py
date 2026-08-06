"""
Specialization Service
Canonical specialization list + synonym mapping.
normalize_strict() — exact/alias only (safe for validation)
normalize()        — full fuzzy (for display)
"""

import difflib
from typing import Optional

CANONICAL_SPECIALIZATIONS = [
    "General Physician", "General Medicine", "Family Medicine", "Emergency Medicine",
    "Cardiology", "Neurology", "Nephrology", "Gastroenterology", "Endocrinology",
    "Pulmonology", "Rheumatology", "Infectious Diseases", "Clinical Immunology",
    "Geriatric Medicine", "Critical Care Medicine",
    "Pediatrics", "Neonatology", "Pediatric Cardiology", "Pediatric Neurology",
    "Pediatric Nephrology", "Pediatric Gastroenterology", "Pediatric Endocrinology",
    "General Surgery", "Orthopedic Surgery", "Neurosurgery", "Plastic Surgery",
    "Cardiothoracic Surgery", "Vascular Surgery", "Urology", "Pediatric Surgery",
    "Surgical Gastroenterology",
    "Obstetrics & Gynecology", "Gynecology", "Reproductive Medicine",
    "Medical Oncology", "Surgical Oncology", "Radiation Oncology",
    "Hematology", "Hemato-Oncology",
    "Dermatology", "Venereology", "Ophthalmology", "ENT", "Psychiatry",
    "Radiology", "Nuclear Medicine", "Pathology", "Microbiology", "Transfusion Medicine",
    "Anesthesiology", "Pain Medicine", "Palliative Medicine",
    "Physical Medicine & Rehabilitation", "Sports Medicine",
    "Dentistry", "Oral & Maxillofacial Surgery",
    "Community Medicine", "Preventive Medicine",
]

TOP_SPECIALIZATIONS = [
    "General Physician", "Cardiology", "Dermatology", "Pediatrics",
    "Orthopedic Surgery", "Obstetrics & Gynecology", "Neurology",
    "Psychiatry", "Ophthalmology", "ENT",
]

SYNONYM_MAP: dict[str, str] = {
    "heart specialist": "Cardiology", "heart doctor": "Cardiology",
    "cardiac specialist": "Cardiology", "cardiologist": "Cardiology",
    "heart surgeon": "Cardiothoracic Surgery", "heart": "Cardiology",
    "brain specialist": "Neurology", "brain doctor": "Neurology",
    "neurologist": "Neurology", "nerve specialist": "Neurology",
    "brain surgeon": "Neurosurgery", "spine surgeon": "Neurosurgery",
    "neurosurgeon": "Neurosurgery",
    "bone doctor": "Orthopedic Surgery", "bone specialist": "Orthopedic Surgery",
    "orthopedic": "Orthopedic Surgery", "orthopaedic": "Orthopedic Surgery",
    "orthopedic surgeon": "Orthopedic Surgery", "orthopaedic surgeon": "Orthopedic Surgery",
    "spine specialist": "Orthopedic Surgery", "joint specialist": "Orthopedic Surgery",
    "skin specialist": "Dermatology", "skin doctor": "Dermatology",
    "dermatologist": "Dermatology", "hair specialist": "Dermatology",
    "child specialist": "Pediatrics", "child doctor": "Pediatrics",
    "pediatrician": "Pediatrics", "paediatrician": "Pediatrics",
    "gynecologist": "Gynecology", "gynaecologist": "Gynecology",
    "women specialist": "Gynecology", "women doctor": "Gynecology",
    "ladies doctor": "Gynecology", "gynecology": "Gynecology",
    "gynaecology": "Gynecology", "female specialist": "Gynecology",
    "obstetrics": "Obstetrics & Gynecology", "obstetrician": "Obstetrics & Gynecology",
    "maternity specialist": "Obstetrics & Gynecology",
    "pregnancy specialist": "Obstetrics & Gynecology",
    "eye specialist": "Ophthalmology", "eye doctor": "Ophthalmology",
    "ophthalmologist": "Ophthalmology", "retina specialist": "Ophthalmology",
    "ear nose throat": "ENT", "ent specialist": "ENT", "ent doctor": "ENT",
    "otolaryngologist": "ENT", "hearing specialist": "ENT",
    "stomach specialist": "Gastroenterology", "gastroenterologist": "Gastroenterology",
    "liver specialist": "Gastroenterology", "digestive specialist": "Gastroenterology",
    "lung specialist": "Pulmonology", "lung doctor": "Pulmonology",
    "chest specialist": "Pulmonology", "pulmonologist": "Pulmonology",
    "respiratory specialist": "Pulmonology", "breathing specialist": "Pulmonology",
    "asthma specialist": "Pulmonology",
    "kidney specialist": "Nephrology", "nephrologist": "Nephrology",
    "diabetes specialist": "Endocrinology", "diabetologist": "Endocrinology",
    "thyroid specialist": "Endocrinology", "endocrinologist": "Endocrinology",
    "urologist": "Urology", "urology": "Urology",
    "mind specialist": "Psychiatry", "psychiatrist": "Psychiatry",
    "mental health specialist": "Psychiatry",
    "cancer specialist": "Medical Oncology", "oncologist": "Medical Oncology",
    "blood specialist": "Hematology", "hematologist": "Hematology",
    "arthritis specialist": "Rheumatology", "rheumatologist": "Rheumatology",
    "radiologist": "Radiology", "imaging specialist": "Radiology",
    "anesthesiologist": "Anesthesiology", "anaesthesiologist": "Anesthesiology",
    "anesthetist": "Anesthesiology", "anaesthetist": "Anesthesiology",
    "surgeon": "General Surgery", "general surgeon": "General Surgery",
    "plastic surgeon": "Plastic Surgery", "cosmetic surgeon": "Plastic Surgery",
    "cardiothoracic surgeon": "Cardiothoracic Surgery",
    "thoracic surgeon": "Cardiothoracic Surgery",
    "general doctor": "General Physician", "general physician": "General Physician",
    "gp": "General Physician", "general practitioner": "General Physician",
    "family doctor": "Family Medicine", "family physician": "Family Medicine",
    "emergency doctor": "Emergency Medicine", "er doctor": "Emergency Medicine",
    "icu specialist": "Critical Care Medicine", "intensivist": "Critical Care Medicine",
    "dentist": "Dentistry", "dental surgeon": "Dentistry",
    "sports doctor": "Sports Medicine",
    "pathologist": "Pathology", "lab specialist": "Pathology",
    "physiotherapist": "Physical Medicine & Rehabilitation",
    "palliative care": "Palliative Medicine", "pain specialist": "Pain Medicine",
    "brain specialist": "Neurology",
}


class SpecializationService:
    _instance = None
    _lower_canonical = [s.lower() for s in CANONICAL_SPECIALIZATIONS]

    @classmethod
    def get_instance(cls) -> "SpecializationService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def normalize_strict(self, text: str) -> Optional[str]:
        """Exact + alias only. No fuzzy. Safe to use on any span."""
        if not text or not text.strip():
            return None
        cleaned = text.strip().lower()
        for i, c in enumerate(self._lower_canonical):
            if cleaned == c:
                return CANONICAL_SPECIALIZATIONS[i]
        for i, c in enumerate(self._lower_canonical):
            if cleaned in c or c in cleaned:
                return CANONICAL_SPECIALIZATIONS[i]
        if cleaned in SYNONYM_MAP:
            return SYNONYM_MAP[cleaned]
        for syn, canon in SYNONYM_MAP.items():
            if syn in cleaned:
                return canon
        return None

    def normalize(self, text: str) -> Optional[str]:
        """Full normalization including fuzzy. For display use."""
        result = self.normalize_strict(text)
        if result:
            return result
        cleaned = text.strip().lower()
        close = difflib.get_close_matches(cleaned, self._lower_canonical, n=1, cutoff=0.6)
        if close:
            return CANONICAL_SPECIALIZATIONS[self._lower_canonical.index(close[0])]
        close_syn = difflib.get_close_matches(cleaned, list(SYNONYM_MAP.keys()), n=1, cutoff=0.6)
        if close_syn:
            return SYNONYM_MAP[close_syn[0]]
        return None

    def get_all(self) -> list[str]:
        return CANONICAL_SPECIALIZATIONS

    def get_top(self, n: int = 10) -> list[str]:
        return TOP_SPECIALIZATIONS[:n]


specialization_service = SpecializationService()
