"""
drx/schemas.py
--------------
Request/response models for DRX integration.
These match what DRX expects — not what onboarding stores internally.
"""

from pydantic import BaseModel
from typing import Optional


class DRXLocationPayload(BaseModel):
    latitude:  Optional[str] = None
    longitude: Optional[str] = None
    address:   Optional[str] = None
    city:      Optional[str] = None
    state:     Optional[str] = None
    country:   Optional[str] = None


class DRXDoctorCreatePayload(BaseModel):
    """What we send to DRX POST /drxdb/integration/doctors/register"""
    name:           str
    username:       Optional[str] = None
    email:          str
    phone:          Optional[str] = None
    password:       Optional[str] = None  # plain text, DRX hashes it
    hospital:       Optional[str] = None
    specialization: Optional[str] = None
    source:         Optional[str] = None  # VOICE | MANUAL
    location:       Optional[DRXLocationPayload] = None


class DRXAuthResponse(BaseModel):
    access_token: str
    expires_in:   int


class DRXDoctorCreateResponse(BaseModel):
    success: bool
    message: str
