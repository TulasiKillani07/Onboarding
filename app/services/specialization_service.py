"""
Specialization Service
Canonical specialization list + synonym mapping + fuzzy matching.
Pipeline: extracted text → exact match → synonym map → fuzzy match → Gemini (last resort)
"""

import difflib
from typing import Optional

# ─────────────────────────────────────────────
# CANONICAL SPECIALIZATION LIST
# ─────────────────────────────────────────────
CANONICAL_SPECIALIZATIONS = [
    # General
    "General Physician",
    "General Medicine",
    "Family Medicine",
    "Emergency Medicine",
    # Internal Medicine
    "Cardiology",
    "Neurology",
    "Nephrology",
    "Gastroenterology",
    "Endocrinology",
    "Pulmonology",
    "Rheumatology",
    "Infectious Diseases",
    "Clinical Immunology",
    "Geriatric Medicine",
    "Critical Care Medicine",
    # Pediatrics
    "Pediatrics",
    "Neonatology",
    "Pediatric Cardiology",
    "Pediatric Neurology",
    "Pediatric Nephrology",
    "Pediatric Gastroenterology",
    "Pediatric Endocrinology",
    # Surgery
    "General Surgery",
    "Orthopedic Surgery",
    "Neurosurgery",
    "Plastic Surgery",
    "Cardiothoracic Surgery",
    "Vascular Surgery",
    "Urology",
    "Pediatric Surgery",
    "Surgical Gastroenterology",
    # OB/GYN
    "Obstetrics & Gynecology",
    "Reproductive Medicine",
    # Oncology
    "Medical Oncology",
    "Surgical Oncology",
    "Radiation Oncology",
    "Hematology",
    "Hemato-Oncology",
    # Skin / Eye / ENT
    "Dermatology",
    "Venereology",
    "Ophthalmology",
    "ENT",
    # Mental Health
    "Psychiatry",
    # Imaging / Lab
    "Radiology",
    "Nuclear Medicine",
    "Pathology",
    "Microbiology",
    "Transfusion Medicine",
    # Anesthesia / Pain
    "Anesthesiology",
    "Pain Medicine",
    "Palliative Medicine",
    # Rehab / Sports
    "Physical Medicine & Rehabilitation",
    "Sports Medicine",
    # Dental
    "Dentistry",
    "Oral & Maxillofacial Surgery",
    # Community
    "Community Medicine",
    "Preventive Medicine",
]

# TOP 10 popular specializations shown first in dropdown
TOP_SPECIALIZATIONS = [
    "General Physician",
    "Cardiology",
    "Dermatology",
    "Pediatrics",
    "Orthopedic Surgery",
    "Obstetrics & Gynecology",
    "Neurology",
    "Psychiatry",
    "Ophthalmology",
    "ENT",
]

# ─────────────────────────────────────────────
# SYNONYM MAP
# Key   = spoken/informal phrase (lowercase)
# Value = canonical specialization name
# ─────────────────────────────────────────────
SYNONYM_MAP: dict[str, str] = {

    # ── Cardiology ──────────────────────────
    "heart specialist": "Cardiology",
    "heart doctor": "Cardiology",
    "heart physician": "Cardiology",
    "cardiac specialist": "Cardiology",
    "cardiac doctor": "Cardiology",
    "cardiologist": "Cardiology",
    "heart surgeon": "Cardiothoracic Surgery",
    "chest heart": "Cardiology",
    "heart": "Cardiology",

    # ── Neurology ───────────────────────────
    "brain specialist": "Neurology",
    "brain doctor": "Neurology",
    "nerve specialist": "Neurology",
    "nerve doctor": "Neurology",
    "neurologist": "Neurology",
    "brain physician": "Neurology",
    "nervous system specialist": "Neurology",
    "brain and spine": "Neurology",

    # ── Neurosurgery ────────────────────────
    "brain surgeon": "Neurosurgery",
    "spine surgeon": "Neurosurgery",
    "neurosurgeon": "Neurosurgery",
    "brain and spine surgeon": "Neurosurgery",

    # ── Orthopedic Surgery ──────────────────
    "bone doctor": "Orthopedic Surgery",
    "bone specialist": "Orthopedic Surgery",
    "bone and joint specialist": "Orthopedic Surgery",
    "joint specialist": "Orthopedic Surgery",
    "orthopedic": "Orthopedic Surgery",
    "orthopaedic": "Orthopedic Surgery",
    "orthopedic surgeon": "Orthopedic Surgery",
    "orthopaedic surgeon": "Orthopedic Surgery",
    "fracture specialist": "Orthopedic Surgery",
    "knee specialist": "Orthopedic Surgery",
    "hip specialist": "Orthopedic Surgery",
    "spine specialist": "Orthopedic Surgery",

    # ── Dermatology ─────────────────────────
    "skin specialist": "Dermatology",
    "skin doctor": "Dermatology",
    "dermatologist": "Dermatology",
    "skin physician": "Dermatology",
    "hair specialist": "Dermatology",
    "hair and skin": "Dermatology",
    "skin and hair": "Dermatology",
    "acne specialist": "Dermatology",

    # ── Pediatrics ──────────────────────────
    "child specialist": "Pediatrics",
    "child doctor": "Pediatrics",
    "children specialist": "Pediatrics",
    "children doctor": "Pediatrics",
    "kids doctor": "Pediatrics",
    "baby doctor": "Pediatrics",
    "pediatrician": "Pediatrics",
    "paediatrician": "Pediatrics",
    "infant specialist": "Pediatrics",
    "child physician": "Pediatrics",

    # ── Gynecology ──────────────────────────
    "gynecologist": "Obstetrics & Gynecology",
    "gynaecologist": "Obstetrics & Gynecology",
    "women specialist": "Obstetrics & Gynecology",
    "women doctor": "Obstetrics & Gynecology",
    "ladies doctor": "Obstetrics & Gynecology",
    "obstetrics": "Obstetrics & Gynecology",
    "gynecology": "Obstetrics & Gynecology",
    "gynaecology": "Obstetrics & Gynecology",
    "obstetrician": "Obstetrics & Gynecology",
    "maternity specialist": "Obstetrics & Gynecology",
    "pregnancy specialist": "Obstetrics & Gynecology",
    "female specialist": "Obstetrics & Gynecology",

    # ── Ophthalmology ───────────────────────
    "eye specialist": "Ophthalmology",
    "eye doctor": "Ophthalmology",
    "eye surgeon": "Ophthalmology",
    "ophthalmologist": "Ophthalmology",
    "vision specialist": "Ophthalmology",
    "retina specialist": "Ophthalmology",

    # ── ENT ─────────────────────────────────
    "ear nose throat": "ENT",
    "ent specialist": "ENT",
    "ent doctor": "ENT",
    "ear specialist": "ENT",
    "throat specialist": "ENT",
    "nose specialist": "ENT",
    "otorhinolaryngologist": "ENT",
    "otolaryngologist": "ENT",
    "hearing specialist": "ENT",

    # ── Gastroenterology ────────────────────
    "stomach specialist": "Gastroenterology",
    "stomach doctor": "Gastroenterology",
    "gastroenterologist": "Gastroenterology",
    "gut specialist": "Gastroenterology",
    "digestive specialist": "Gastroenterology",
    "liver specialist": "Gastroenterology",
    "liver doctor": "Gastroenterology",
    "intestine specialist": "Gastroenterology",
    "digestion specialist": "Gastroenterology",

    # ── Pulmonology ─────────────────────────
    "lung specialist": "Pulmonology",
    "lung doctor": "Pulmonology",
    "chest specialist": "Pulmonology",
    "chest doctor": "Pulmonology",
    "pulmonologist": "Pulmonology",
    "respiratory specialist": "Pulmonology",
    "breathing specialist": "Pulmonology",
    "asthma specialist": "Pulmonology",
    "respiratory medicine": "Pulmonology",

    # ── Nephrology ──────────────────────────
    "kidney specialist": "Nephrology",
    "kidney doctor": "Nephrology",
    "nephrologist": "Nephrology",
    "renal specialist": "Nephrology",

    # ── Endocrinology ───────────────────────
    "diabetes specialist": "Endocrinology",
    "diabetologist": "Endocrinology",
    "hormone specialist": "Endocrinology",
    "thyroid specialist": "Endocrinology",
    "endocrinologist": "Endocrinology",
    "sugar specialist": "Endocrinology",
    "diabetes doctor": "Endocrinology",

    # ── Urology ─────────────────────────────
    "urologist": "Urology",
    "urology": "Urology",
    "kidney and bladder": "Urology",
    "prostate specialist": "Urology",
    "bladder specialist": "Urology",

    # ── Psychiatry ──────────────────────────
    "mind specialist": "Psychiatry",
    "mind doctor": "Psychiatry",
    "mental health specialist": "Psychiatry",
    "mental health doctor": "Psychiatry",
    "psychiatrist": "Psychiatry",
    "psychological specialist": "Psychiatry",
    "mental specialist": "Psychiatry",

    # ── Oncology ────────────────────────────
    "cancer specialist": "Medical Oncology",
    "cancer doctor": "Medical Oncology",
    "oncologist": "Medical Oncology",
    "tumor specialist": "Medical Oncology",
    "cancer surgeon": "Surgical Oncology",
    "radiation specialist": "Radiation Oncology",

    # ── Hematology ──────────────────────────
    "blood specialist": "Hematology",
    "blood doctor": "Hematology",
    "hematologist": "Hematology",

    # ── Rheumatology ────────────────────────
    "joint pain specialist": "Rheumatology",
    "arthritis specialist": "Rheumatology",
    "rheumatologist": "Rheumatology",

    # ── Radiology ───────────────────────────
    "radiologist": "Radiology",
    "x-ray specialist": "Radiology",
    "scan specialist": "Radiology",
    "imaging specialist": "Radiology",

    # ── Anesthesiology ──────────────────────
    "anesthesiologist": "Anesthesiology",
    "anaesthesiologist": "Anesthesiology",
    "anesthetist": "Anesthesiology",
    "anaesthetist": "Anesthesiology",

    # ── General Surgery ─────────────────────
    "surgeon": "General Surgery",
    "general surgeon": "General Surgery",

    # ── Plastic Surgery ─────────────────────
    "plastic surgeon": "Plastic Surgery",
    "cosmetic surgeon": "Plastic Surgery",
    "cosmetic specialist": "Plastic Surgery",

    # ── Cardiothoracic Surgery ───────────────
    "cardiothoracic surgeon": "Cardiothoracic Surgery",
    "heart and chest surgeon": "Cardiothoracic Surgery",
    "thoracic surgeon": "Cardiothoracic Surgery",

    # ── General Physician ───────────────────
    "general doctor": "General Physician",
    "general physician": "General Physician",
    "gp": "General Physician",
    "general practitioner": "General Physician",
    "family doctor": "Family Medicine",
    "family physician": "Family Medicine",

    # ── Emergency Medicine ──────────────────
    "emergency doctor": "Emergency Medicine",
    "er doctor": "Emergency Medicine",
    "casualty doctor": "Emergency Medicine",
    "emergency physician": "Emergency Medicine",

    # ── Critical Care ───────────────────────
    "icu specialist": "Critical Care Medicine",
    "intensive care": "Critical Care Medicine",
    "intensivist": "Critical Care Medicine",
    "critical care": "Critical Care Medicine",

    # ── Dentistry ───────────────────────────
    "dentist": "Dentistry",
    "dental surgeon": "Dentistry",
    "teeth specialist": "Dentistry",
    "tooth specialist": "Dentistry",
    "oral specialist": "Dentistry",

    # ── Sports Medicine ─────────────────────
    "sports doctor": "Sports Medicine",
    "sports physician": "Sports Medicine",
    "sports injury specialist": "Sports Medicine",

    # ── Pathology ───────────────────────────
    "pathologist": "Pathology",
    "lab specialist": "Pathology",
    "laboratory specialist": "Pathology",

    # ── Venereology ─────────────────────────
    "skin and sexual diseases": "Venereology",
    "std specialist": "Venereology",

    # ── Physical Medicine ───────────────────
    "physiotherapist": "Physical Medicine & Rehabilitation",
    "physio": "Physical Medicine & Rehabilitation",
    "rehabilitation specialist": "Physical Medicine & Rehabilitation",
    "rehab specialist": "Physical Medicine & Rehabilitation",

    # ── Palliative Medicine ─────────────────
    "palliative care": "Palliative Medicine",
    "pain specialist": "Pain Medicine",

    # ── Community / Preventive ──────────────
    "community doctor": "Community Medicine",
    "public health doctor": "Preventive Medicine",
    "preventive specialist": "Preventive Medicine",
}


class SpecializationService:
    """
    Normalizes any spoken/extracted department text to a canonical specialization.
    Pipeline: exact → synonym map → fuzzy → None
    """

    _instance = None
    # Lowercase canonical list for matching
    _lower_canonical = [s.lower() for s in CANONICAL_SPECIALIZATIONS]

    @classmethod
    def get_instance(cls) -> "SpecializationService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def normalize(self, text: str) -> Optional[str]:
        """
        Normalize extracted department text to canonical specialization.
        Returns canonical name or None if no match found.
        """
        if not text or not text.strip():
            return None

        cleaned = text.strip().lower()

        # 1. Exact match against canonical list (case-insensitive)
        for i, canon_lower in enumerate(self._lower_canonical):
            if cleaned == canon_lower:
                return CANONICAL_SPECIALIZATIONS[i]

        # 2. Canonical contains extracted text or vice versa
        for i, canon_lower in enumerate(self._lower_canonical):
            if cleaned in canon_lower or canon_lower in cleaned:
                return CANONICAL_SPECIALIZATIONS[i]

        # 3. Synonym map lookup
        if cleaned in SYNONYM_MAP:
            return SYNONYM_MAP[cleaned]

        # 4. Partial synonym match (extracted text contains a synonym key)
        for synonym, canonical in SYNONYM_MAP.items():
            if synonym in cleaned or cleaned in synonym:
                return canonical

        # 5. Word-level synonym match
        # e.g. "I am a heart specialist" → look for synonym keys in the text
        words_in_text = cleaned.split()
        for synonym, canonical in SYNONYM_MAP.items():
            synonym_words = synonym.split()
            # Check if all words of synonym appear in the text
            if all(w in words_in_text for w in synonym_words):
                return canonical

        # 6. Fuzzy match against canonical list using difflib
        close = difflib.get_close_matches(
            cleaned,
            self._lower_canonical,
            n=1,
            cutoff=0.6,
        )
        if close:
            idx = self._lower_canonical.index(close[0])
            return CANONICAL_SPECIALIZATIONS[idx]

        # 7. Fuzzy match against synonym keys
        close_syn = difflib.get_close_matches(
            cleaned,
            list(SYNONYM_MAP.keys()),
            n=1,
            cutoff=0.6,
        )
        if close_syn:
            return SYNONYM_MAP[close_syn[0]]

        return None

    def get_all(self) -> list[str]:
        """Return full canonical specialization list."""
        return CANONICAL_SPECIALIZATIONS

    def get_top(self, n: int = 10) -> list[str]:
        """Return top N popular specializations."""
        return TOP_SPECIALIZATIONS[:n]


# Singleton instance
specialization_service = SpecializationService()
