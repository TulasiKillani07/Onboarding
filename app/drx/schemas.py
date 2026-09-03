"""
drx/schemas.py
--------------
Request/response models for DRX integration.
These match what DRX expects — not what onboarding stores internally.
"""

from pydantic import BaseModel
from typing import Optional, List


class DRXLocationPayload(BaseModel):
    location_priority:   Optional[str] = None
    facility_type:       Optional[str] = None
    facility_type_other: Optional[str] = None
    location_name:       Optional[str] = None
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
    status:              Optional[str] = None


class DRXDoctorCreatePayload(BaseModel):
    """What we send to DRX POST /drxdb/integration/doctors/register"""
    name:                 str
    username:             Optional[str] = None
    email:                str
    phone:                Optional[str] = None
    password:             Optional[str] = None  # plain text, DRX hashes it
    specialization:       Optional[str] = None
    source:               Optional[str] = None  # VOICE | MANUAL
    locations:            Optional[List[DRXLocationPayload]] = None


class DRXAuthResponse(BaseModel):
    access_token: str
    expires_in:   int


class DRXDoctorCreateResponse(BaseModel):
    success: bool
    message: str
