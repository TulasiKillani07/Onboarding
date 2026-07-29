"""
Regex extraction service for structured data.
Extracts phone numbers and email addresses from transcripts.
Handles spoken numbers (eight double three one zero...) and spoken emails.
"""

import re
from typing import Dict, Optional


# Word-to-digit mapping
WORD_TO_DIGIT = {
    "zero": "0", "oh": "0", "o": "0",
    "one": "1", "won": "1",
    "two": "2", "to": "2", "too": "2",
    "three": "3", "tree": "3",
    "four": "4", "for": "4",
    "five": "5",
    "six": "6", "sicks": "6",
    "seven": "7",
    "eight": "8", "ate": "8",
    "nine": "9", "niner": "9",
}

# Double/triple words
MULTIPLIER_WORDS = {
    "double": 2, "triple": 3,
}


class RegexService:
    """Service for extracting structured data using regex patterns."""

    # Indian mobile number: 10 digits, optionally prefixed with +91 or 0
    PHONE_PATTERNS = [
        r'\+91[\s-]?(\d{10})',
        r'\b0?(\d{10})\b',
        r'(\d{5}[\s-]?\d{5})',
        r'(?:phone|mobile|number|contact)[\s:]*(?:\+91[\s-]?)?(\d{10})',
    ]

    # Email pattern
    EMAIL_PATTERNS = [
        r'[\w.+-]+@[\w-]+\.[\w.-]+',
    ]

    @staticmethod
    def spoken_number_to_digits(text: str) -> str:
        """
        Convert spoken number words to digit string.
        E.g., "eight double three one zero eight six seven one nine" → "8331086719"
        """
        words = text.lower().split()
        digits = []
        i = 0

        while i < len(words):
            word = words[i]

            # Check for multiplier (double, triple)
            if word in MULTIPLIER_WORDS and i + 1 < len(words):
                next_word = words[i + 1]
                if next_word in WORD_TO_DIGIT:
                    digit = WORD_TO_DIGIT[next_word]
                    digits.append(digit * MULTIPLIER_WORDS[word])
                    i += 2
                    continue
                elif next_word.isdigit() and len(next_word) == 1:
                    digits.append(next_word * MULTIPLIER_WORDS[word])
                    i += 2
                    continue

            # Check for digit word
            if word in WORD_TO_DIGIT:
                digits.append(WORD_TO_DIGIT[word])
            elif word.isdigit():
                digits.append(word)

            i += 1

        return "".join(digits)

    @classmethod
    def extract_phone(cls, text: str) -> Optional[str]:
        """
        Extract Indian mobile number from text.
        Handles both digit sequences and spoken number words.
        """
        # Normalize text
        normalized = text.lower().replace(",", "").replace("-", " ")

        # First try: find actual digit sequences
        for pattern in cls.PHONE_PATTERNS:
            match = re.search(pattern, normalized)
            if match:
                phone = re.sub(r'\D', '', match.group(0))
                if len(phone) >= 10:
                    phone = phone[-10:]
                    if phone[0] in '6789':
                        return phone

        # Fallback: find any 10-digit sequence
        all_digits = re.findall(r'\d+', text)
        for digits in all_digits:
            if len(digits) == 10 and digits[0] in '6789':
                return digits

        # Try concatenating adjacent digit groups
        digit_groups = re.findall(r'\d+', normalized)
        if digit_groups:
            combined = "".join(digit_groups)
            if len(combined) >= 10:
                phone = combined[-10:]
                if phone[0] in '6789':
                    return phone

        # Try spoken number conversion
        # Look for phone context then convert words after it
        phone_context = re.search(
            r'(?:phone|mobile|number|contact|call)[\s:]*(.+?)(?:\.|,|and|$)',
            normalized
        )
        if phone_context:
            spoken_digits = cls.spoken_number_to_digits(phone_context.group(1))
            if len(spoken_digits) >= 10:
                phone = spoken_digits[-10:]
                if phone[0] in '6789':
                    return phone

        # Last resort: try converting the entire text's number words
        spoken_digits = cls.spoken_number_to_digits(normalized)
        if len(spoken_digits) >= 10:
            phone = spoken_digits[-10:]
            if phone[0] in '6789':
                return phone

        return None

    @staticmethod
    def extract_email(text: str) -> Optional[str]:
        """
        Extract email address from text.
        Handles direct emails and spoken format (e.g. "vamsi wakad 163 at the rate gmail dot com")
        """
        # Direct email pattern
        match = re.search(r'[\w.+-]+@[\w-]+\.[\w.-]+', text)
        if match:
            email = match.group(0).lower().rstrip(".")
            if RegexService.validate_email(email):
                return email

        text_lower = text.lower()

        # Handle spoken email with various "at" patterns
        # "vamsi wakad 163 at the rate gmail dot com"
        # "rahul at gmail dot com"
        # "rahul at the rate of gmail dot com"
        spoken_patterns = [
            r'([\w\s]+?)\s*(?:at the rate of|at the rate|at)\s*([\w]+)\s*(?:dot|\.)\s*([\w]+)',
        ]

        for pattern in spoken_patterns:
            match = re.search(pattern, text_lower)
            if match:
                username = match.group(1).strip()
                domain = match.group(2).strip()
                tld = match.group(3).strip()

                # Clean username: remove spaces, keep alphanumeric and dots
                username = re.sub(r'\s+', '', username)
                # Remove common filler words that might be in the username
                username = re.sub(r'\b(my|email|is|id|address|mail)\b', '', username).strip()

                if username and domain and tld:
                    email = f"{username}@{domain}.{tld}"
                    if RegexService.validate_email(email):
                        return email

        # Simpler pattern: "X at Y dot Z"
        match = re.search(
            r'(\w[\w.]*)\s*(?:at|@)\s*(\w+)\s*(?:dot|\.)\s*(\w+)',
            text_lower
        )
        if match:
            email = f"{match.group(1)}@{match.group(2)}.{match.group(3)}"
            if RegexService.validate_email(email):
                return email

        return None

    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format."""
        pattern = r'^[\w.+-]+@[\w-]+\.[\w.-]+$'
        return bool(re.match(pattern, email))

    @staticmethod
    def validate_phone(phone: str) -> bool:
        """Validate Indian mobile number."""
        pattern = r'^[6-9]\d{9}$'
        return bool(re.match(pattern, phone))

    @classmethod
    def extract_all(cls, text: str) -> Dict[str, Optional[str]]:
        """
        Extract all regex-matchable fields from text.
        """
        return {
            "phone": cls.extract_phone(text),
            "email": cls.extract_email(text),
        }
