"""
onboarding/models.py
--------------------
MongoDB document models for onboarding.doctors collection.

The onboarding database stores the doctor exactly as submitted.
It is NOT the source of truth — DRX is.

IDs:
  _id → MongoDB ObjectId (auto-generated, identifies this onboarding record)

doctor_gid is NOT generated here. That belongs to DRX.

Locations:
  A doctor practices at one or more locations. Each location has a priority
  (PRIMARY / SECONDARY / OTHER) and a facility_type (HOSPITAL / CLINIC / ...).
  Exactly one PRIMARY is required. At most one SECONDARY. Any number of OTHER.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List
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


class LocationPriority(str, Enum):
    PRIMARY   = "PRIMARY"
    SECONDARY = "SECONDARY"
    OTHER     = "OTHER"


class FacilityType(str, Enum):
    HOSPITAL                    = "HOSPITAL"
    CLINIC                      = "CLINIC"
    POLYCLINIC                  = "POLYCLINIC"
    MEDICAL_CENTER              = "MEDICAL_CENTER"
    INSTITUTION_MEDICAL_COLLEGE = "INSTITUTION OR MEDICAL COLLEGE"
    OTHER                       = "OTHER"


class LocationSource(str, Enum):
    CURRENT_LOCATION = "CURRENT_LOCATION"
    MAP_SEARCH       = "MAP_SEARCH"
    MANUAL           = "MANUAL"


class LocationModel(BaseModel):
    location_priority:   str           = LocationPriority.PRIMARY.value
    facility_type:       str           = FacilityType.HOSPITAL.value
    facility_type_other: Optional[str] = None
    location_name:       Optional[str] = None  # institution / hospital / clinic name
    latitude:            Optional[str] = None
    longitude:           Optional[str] = None
    address:             Optional[str] = None
    area:                Optional[str] = None
    city:                Optional[str] = None
    district:            Optional[str] = None
    state:               Optional[str] = None
    country:             Optional[str] = None
    postcode:            Optional[str] = None
    location_source:     Optional[str] = None
    status:              str           = Status.ACTIVE.value


class DoctorDocument(BaseModel):
    """Pydantic model for the onboarding.doctors MongoDB document."""

    doctor_name:         str
    username:            str
    password_hash:       str
    email:               Optional[str] = None
    phone:               Optional[str] = None
    specialization:      Optional[str] = None
    source:              str
    locations:           List[LocationModel] = Field(default_factory=list)
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


def validate_locations(locations: List[dict]) -> Optional[str]:
    """
    Enforce location priority rules:
      - PRIMARY   → exactly 1 (required)
      - SECONDARY → at most 1
      - OTHER     → any number

    Returns an error message string if invalid, or None if valid.
    """
    if not locations:
        return "At least one location is required (with location_priority=PRIMARY)."

    primary_count   = sum(1 for l in locations if l.get("location_priority") == LocationPriority.PRIMARY.value)
    secondary_count = sum(1 for l in locations if l.get("location_priority") == LocationPriority.SECONDARY.value)

    if primary_count != 1:
        return f"Exactly one PRIMARY location is required (found {primary_count})."
    if secondary_count > 1:
        return f"At most one SECONDARY location is allowed (found {secondary_count})."
    return None


def new_doctor_document(
    doctor_name:         str,
    username:            str,
    password_hash:       str,
    email:               Optional[str],
    phone:               Optional[str],
    specialization:      Optional[str],
    source:              Source,
    locations:           Optional[List[dict]] = None,
) -> dict:
    """
    Build a new doctor document for insertion into onboarding.doctors.
    Uses DoctorDocument Pydantic model for validation and structure.
    Returns a plain dict ready for Motor insert_one().
    """
    loc_models = [LocationModel(**loc) for loc in (locations or [])]

    doc = DoctorDocument(
        doctor_name=doctor_name,
        username=username,
        password_hash=password_hash,
        email=email or None,
        phone=phone or None,
        specialization=specialization or None,
        source=source.value,
        locations=loc_models,
    )

    return doc.to_mongo()
