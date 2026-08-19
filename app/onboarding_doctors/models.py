"""
onboarding/models.py
--------------------
MongoDB document models for onboarding.doctors collection.

The onboarding database stores the doctor exactly as submitted.
It is NOT the source of truth — DRX is.

IDs:
  _id → MongoDB ObjectId (auto-generated, identifies this onboarding record)

doctor_gid is NOT generated here. That belongs to DRX.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


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


class LocationModel(BaseModel):
    latitude:  Optional[str] = None
    longitude: Optional[str] = None
    address:   Optional[str] = None
    city:      Optional[str] = None
    state:     Optional[str] = None
    country:   Optional[str] = None


class DoctorDocument(BaseModel):
    """Pydantic model for the onboarding.doctors MongoDB document."""

    doctor_name:    str
    username:       str
    password_hash:  str
    email:          Optional[str] = None
    phone:          Optional[str] = None
    hospital:       Optional[str] = None
    specialization: Optional[str] = None
    source:         str
    location:       LocationModel = Field(default_factory=LocationModel)
    status:         str = Status.ACTIVE.value
    sync_status:    str = SyncStatus.PENDING.value
    sync_error:     Optional[str] = None
    sync_attempts:  int = 0
    last_sync_attempt: Optional[datetime] = None
    created_at:     datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at:     datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def to_mongo(self) -> dict:
        """Convert to dict for MongoDB insert_one()."""
        return self.model_dump()


def new_doctor_document(
    doctor_name:    str,
    username:       str,
    password_hash:  str,
    email:          Optional[str],
    phone:          Optional[str],
    hospital:       Optional[str],
    specialization: Optional[str],
    source:         Source,
    location:       Optional[dict] = None,
) -> dict:
    """
    Build a new doctor document for insertion into onboarding.doctors.
    Uses DoctorDocument Pydantic model for validation and structure.
    Returns a plain dict ready for Motor insert_one().
    """
    loc = LocationModel(**(location or {}))

    doc = DoctorDocument(
        doctor_name=doctor_name,
        username=username,
        password_hash=password_hash,
        email=email or None,
        phone=phone or None,
        hospital=hospital or None,
        specialization=specialization or None,
        source=source.value,
        location=loc,
    )

    return doc.to_mongo()
