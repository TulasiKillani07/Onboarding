"""
onboarding_sessions/models.py
------------------------------
MongoDB document model for onboarding.onboarding_sessions collection.

Each onboarding attempt (voice or manual) creates one session document.
Purpose: audit, debugging, retraining, user corrections tracking.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional


def generate_session_id() -> str:
    """Generate a unique session_id."""
    return str(uuid.uuid4())


def new_session_document(
    session_id:       str,
    onboarding_id:        str,               # MongoDB _id of the onboarding doctor
    source:           str,               # VOICE | MANUAL
    transcript:       Optional[str] = None,
    ner_output:       Optional[dict] = None,
    pipeline_output:  Optional[dict] = None,
    auto_fill:        Optional[dict] = None,
    corrections:      Optional[dict] = None,
    final_submission: Optional[dict] = None,
) -> dict:
    """
    Build a new session document for insertion into onboarding.onboarding_sessions.
    """
    return {
        "session_id":       session_id,
        "onboarding_id":        onboarding_id,
        "source":           source,

        # Voice-specific (null for manual sessions)
        "transcript":       transcript,
        "ner_output":       ner_output,
        "pipeline_output":  pipeline_output,
        "auto_fill":        auto_fill,

        # What the doctor changed from auto-fill (valuable for retraining)
        "corrections":      corrections,

        # Final submitted data (both voice and manual)
        "final_submission": final_submission,

        # Status
        "status":           "COMPLETED",

        # Timestamp
        "created_at":       datetime.now(timezone.utc),
    }

