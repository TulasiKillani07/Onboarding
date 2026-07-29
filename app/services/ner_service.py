"""
Named Entity Recognition service using spaCy.
Custom entity extraction for doctor registration: PERSON_NAME, HOSPITAL, DEPARTMENT.
"""

import re
import spacy
from typing import Dict, Optional


# Known hospitals for pattern matching
KNOWN_HOSPITALS = [
    "apollo hospital", "apollo hospitals", "apollo clinic",
    "fortis hospital", "fortis healthcare",
    "max hospital", "max healthcare",
    "aiims", "all india institute of medical sciences",
    "medanta", "medanta hospital",
    "narayana health", "narayana hospital",
    "manipal hospital", "manipal hospitals",
    "columbia asia", "columbia asia hospital",
    "lilavati hospital",
    "kokilaben hospital", "kokilaben dhirubhai ambani",
    "aig hospital", "aig hospitals",
    "kims hospital", "kims",
    "care hospital", "care hospitals",
    "yashoda hospital", "yashoda hospitals",
    "global hospital", "global hospitals",
    "rainbow hospital", "rainbow hospitals",
    "star hospital", "star hospitals",
    "continental hospital", "continental hospitals",
    "aware gleneagles", "gleneagles hospital",
    "sunshine hospital", "sunshine hospitals",
    "citizens hospital",
    "omni hospital",
]

# Known departments / specializations
KNOWN_DEPARTMENTS = [
    "cardiology", "cardiologist",
    "neurology", "neurologist",
    "orthopedics", "orthopedic", "orthopaedics",
    "dermatology", "dermatologist",
    "pediatrics", "pediatrician", "paediatrics",
    "gynecology", "gynecologist", "gynaecology",
    "ophthalmology", "ophthalmologist",
    "ent", "otolaryngology",
    "gastroenterology", "gastroenterologist",
    "pulmonology", "pulmonologist",
    "nephrology", "nephrologist",
    "urology", "urologist",
    "oncology", "oncologist",
    "radiology", "radiologist",
    "anesthesiology", "anesthesiologist",
    "psychiatry", "psychiatrist",
    "endocrinology", "endocrinologist",
    "rheumatology", "rheumatologist",
    "hematology", "hematologist",
    "general medicine", "general physician",
    "general surgery", "surgeon",
    "plastic surgery", "plastic surgeon",
    "vascular surgery",
    "cardiac surgery", "cardiac surgeon",
    "neuro surgery", "neurosurgeon",
    "internal medicine", "internist",
    "family medicine",
    "emergency medicine",
    "critical care", "intensivist",
    "pathology", "pathologist",
    "microbiology",
    "physiotherapy", "physiotherapist",
    "dentistry", "dentist",
    "ayurveda",
    "homeopathy",
]

# Words that should NOT be considered as names
NON_NAME_WORDS = {
    "hospital", "hospitals", "clinic", "clinics", "department", "india",
    "city", "doctor", "phone", "email", "number", "mobile", "contact",
    "work", "working", "practice", "name", "the", "and", "from", "with",
    "my", "is", "am", "at", "in", "of", "a", "an", "i", "me",
    "cardiology", "neurology", "dermatology", "orthopedics", "pediatrics",
    "gynecology", "ophthalmology", "gastroenterology", "pulmonology",
    "nephrology", "urology", "oncology", "radiology", "psychiatry",
    "cardiologist", "neurologist", "dermatologist", "surgeon",
    "gmail", "yahoo", "hotmail", "com", "dot", "rate",
}


class NERService:
    """Custom NER service for doctor registration entity extraction."""

    _instance = None
    _nlp = None

    @classmethod
    def get_instance(cls) -> "NERService":
        """Singleton pattern for model reuse."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        """Initialize spaCy with custom entity rules."""
        if NERService._nlp is None:
            try:
                NERService._nlp = spacy.load("en_core_web_sm")
            except OSError:
                NERService._nlp = spacy.blank("en")

            # Add custom entity ruler
            if "entity_ruler" not in NERService._nlp.pipe_names:
                ruler = NERService._nlp.add_pipe(
                    "entity_ruler",
                    before="ner" if "ner" in NERService._nlp.pipe_names else None
                )
                patterns = []

                for hospital in KNOWN_HOSPITALS:
                    patterns.append({"label": "HOSPITAL", "pattern": hospital.title()})
                    patterns.append({"label": "HOSPITAL", "pattern": hospital.upper()})
                    words = hospital.split()
                    if len(words) > 1:
                        patterns.append({"label": "HOSPITAL", "pattern": [{"LOWER": w} for w in words]})

                for dept in KNOWN_DEPARTMENTS:
                    patterns.append({"label": "DEPARTMENT", "pattern": dept.title()})
                    patterns.append({"label": "DEPARTMENT", "pattern": [{"LOWER": w} for w in dept.split()]})

                ruler.add_patterns(patterns)

    def extract_entities(self, text: str) -> Dict[str, Optional[str]]:
        """Extract named entities from transcript text."""
        doc = NERService._nlp(text)

        entities = {
            "PERSON_NAME": None,
            "HOSPITAL": None,
            "DEPARTMENT": None,
        }

        # Extract from spaCy NER
        for ent in doc.ents:
            if ent.label_ == "PERSON" and entities["PERSON_NAME"] is None:
                name = ent.text.strip()
                if self._is_valid_name(name):
                    entities["PERSON_NAME"] = name
            elif ent.label_ == "HOSPITAL" and entities["HOSPITAL"] is None:
                entities["HOSPITAL"] = ent.text.strip()
            elif ent.label_ == "DEPARTMENT" and entities["DEPARTMENT"] is None:
                entities["DEPARTMENT"] = ent.text.strip()

        # Aggressive fallbacks
        if entities["PERSON_NAME"] is None:
            entities["PERSON_NAME"] = self._extract_name_fallback(text)

        if entities["HOSPITAL"] is None:
            entities["HOSPITAL"] = self._extract_hospital_fallback(text)

        if entities["DEPARTMENT"] is None:
            entities["DEPARTMENT"] = self._extract_department_fallback(text)

        return entities

    def _is_valid_name(self, name: str) -> bool:
        """Check if text is likely a person's name."""
        words = name.lower().split()
        # All words should not be in non-name list
        if all(w in NON_NAME_WORDS for w in words):
            return False
        # Should not contain digits
        if any(c.isdigit() for c in name):
            return False
        # At least 2 characters
        if len(name.strip()) < 2:
            return False
        # Should not be a known hospital or department
        if name.lower() in [h for h in KNOWN_HOSPITALS] + [d for d in KNOWN_DEPARTMENTS]:
            return False
        return True

    def _extract_name_fallback(self, text: str) -> Optional[str]:
        """
        Aggressive name extraction fallback.
        Handles: "My name is Pavani", "I am Dr Vamshi", "name is vamshi wakad", etc.
        Case-insensitive to handle Sarvam's translation output.
        """
        # Patterns ordered from most specific to least specific
        patterns = [
            # "my name is Dr. Pavani Sharma"
            r'(?:my\s+name\s+is|i\s+am|i\'m|this\s+is)\s+(?:dr\.?\s+|doctor\s+)?(.+?)(?:\.|,|and\s+|i\s+work|i\s+am\s+a|i\s+am\s+an|my\s+phone|my\s+email|my\s+number|phone|email|$)',
            # "name is Pavani"
            r'name\s+is\s+(?:dr\.?\s+|doctor\s+)?(.+?)(?:\.|,|and\s+|i\s+work|i\s+am|my\s+|phone|email|$)',
            # "Dr Pavani" or "Dr. Vamshi Sharma"
            r'(?:dr\.?|doctor)\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)?)',
            # "I'm Pavani, a dermatologist" — name before department
            r'(?:i\s+am|i\'m)\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)?)\s*[,.]',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                # Clean up trailing words
                name = re.sub(r'\s+(and|from|at|in|the|my|i)\b.*$', '', name, flags=re.IGNORECASE)
                # Remove trailing punctuation
                name = name.rstrip('.,;:')
                # Validate
                if name and self._is_valid_name(name) and len(name) >= 3:
                    # Title case the name
                    name = name.title()
                    # Add Dr prefix if not present
                    if not name.lower().startswith("dr"):
                        name = f"Dr {name}"
                    return name

        return None

    def _extract_hospital_fallback(self, text: str) -> Optional[str]:
        """Fallback hospital extraction."""
        text_lower = text.lower()

        # Check known hospitals
        for hospital in KNOWN_HOSPITALS:
            if hospital in text_lower:
                return hospital.title()

        # Pattern matching
        patterns = [
            r'(?:work|working|practice|practicing|practise)\s+(?:at|in)\s+(.+?(?:hospital|clinic|medical|healthcare|health|centre|center))',
            r'(?:from|at|in)\s+(.+?(?:hospital|clinic|medical|healthcare|health|centre|center))',
            r'(.+?(?:hospital|clinic|medical center|healthcare))',
        ]

        for pattern in patterns:
            match = re.search(pattern, text_lower)
            if match:
                hospital = match.group(1).strip()
                # Clean and validate
                hospital = re.sub(r'^(i\s+work\s+|i\s+am\s+|from\s+)', '', hospital)
                if len(hospital) >= 3 and hospital not in NON_NAME_WORDS:
                    return hospital.title()

        return None

    def _extract_department_fallback(self, text: str) -> Optional[str]:
        """Fallback department extraction."""
        text_lower = text.lower()

        for dept in KNOWN_DEPARTMENTS:
            if dept in text_lower:
                return dept.title()

        return None
