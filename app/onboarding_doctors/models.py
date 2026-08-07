"""
onboarding/models.py
--------------------
MongoDB document model for onboarding.doctors collection.

The onboarding database stores the doctor exactly as submitted.
It is NOT the source of truth — DRX is.

IDs:
  _id         → MongoDB ObjectId (auto-generated, identifies this onboarding record)
  drx_doctor_gid → filled only after DRX successfully creates the doctor

doctor_gid is NOT generated here. That belongs to DRX.
"""

from datetime import datetime, timezone
from enum import Enum


class Source(str, Enum):
    VOICE  = "VOICE"
    MANUAL = "MANUAL"


class Status(str, Enum):
    ACTIVE   = "ACTIVE"
    INACTIVE = "INACTIVE"


class SyncStatus(str, Enum):
    PENDING = "PENDING"
    SYNCED  = "SYNCED"
    FAILED  = "FAILED"


def new_doctor_document(
    doctor_name:    str,
    email:          str | None,
    phone:          str | None,
    hospital:       str | None,
    specialization: str | None,
    source:         Source,
    location:       dict | None = None,
) -> dict:
    """
    Build a new doctor document for insertion into onboarding.doctors.
    Returns a plain dict ready for Motor insert_one().
    """
    now = datetime.now(timezone.utc)
    return {
        # Registration data — exactly as submitted
        "doctor_name":    doctor_name,
        "email":          email or None,
        "phone":          phone or None,
        "hospital":       hospital or None,
        "specialization": specialization or None,
        "source":         source.value,

        # Location — as submitted by frontend
        "location": location or {
            "latitude":  None,
            "longitude": None,
            "address":   None,
            "city":      None,
            "state":     None,
            "country":   None,
        },

        # Status
        "status":      Status.ACTIVE.value,
        "sync_status": SyncStatus.PENDING.value,
        "sync_error":  None,

        # Timestamps
        "created_at": now,
        "updated_at": now,
    }
