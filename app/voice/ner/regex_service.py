"""
Regex Service
Extracts PHONE and EMAIL from text.
"""

import re
from typing import Optional

PHONE_RE = re.compile(
    r"(\+91[\s\-]?)?[6-9]\d{9}"
    r"|(\+91[\s\-]?)?\d{3,5}[\s\-]\d{4,8}"
    r"|\b\d{10}\b"
    r"|\+\d{1,3}[\s\-]\d{6,12}"
)
EMAIL_RE = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")


def extract_phones(text: str) -> list[dict]:
    return [{"text": m.group().strip(), "start": m.start(), "end": m.end()}
            for m in PHONE_RE.finditer(text) if m.group().strip()]


def extract_emails(text: str) -> list[dict]:
    return [{"text": m.group().rstrip(".,;:"), "start": m.start(), "end": m.end()}
            for m in EMAIL_RE.finditer(text)]

