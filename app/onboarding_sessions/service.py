"""
onboarding_sessions/service.py
-------------------------------
Responsibilities:
  - Generate session_id
  - Save onboarding session
  - Get session by id
  - List sessions for a doctor

No business logic. Pure persistence.
"""

from app.database import get_database, COLLECTION_ONBOARDING_SESSIONS
from app.onboarding_sessions.models import generate_session_id, new_session_document
from typing import Optional


async def create_session(
    onboarding_id:        str,
    source:           str,
    final_submission: dict,
    transcript:       Optional[str] = None,
    ner_output:       Optional[dict] = None,
    pipeline_output:  Optional[dict] = None,
    auto_fill:        Optional[dict] = None,
    corrections:      Optional[dict] = None,
) -> dict:
    """
    Create and save a new onboarding session.
    Returns the session document with session_id.
    """
    db  = get_database()
    col = db[COLLECTION_ONBOARDING_SESSIONS]

    session_id = generate_session_id()
    doc = new_session_document(
        session_id=session_id,
        onboarding_id=onboarding_id,
        source=source,
        transcript=transcript,
        ner_output=ner_output,
        pipeline_output=pipeline_output,
        auto_fill=auto_fill,
        corrections=corrections,
        final_submission=final_submission,
    )

    await col.insert_one(doc)
    return doc


async def get_session(session_id: str) -> Optional[dict]:
    """Get a single session by session_id."""
    db  = get_database()
    col = db[COLLECTION_ONBOARDING_SESSIONS]
    return await col.find_one({"session_id": session_id})


async def list_sessions_for_doctor(onboarding_id: str) -> list[dict]:
    """List all sessions for a given doctor, newest first."""
    db  = get_database()
    col = db[COLLECTION_ONBOARDING_SESSIONS]
    cursor = col.find({"onboarding_id": onboarding_id}).sort("created_at", -1)
    return await cursor.to_list(length=100)

