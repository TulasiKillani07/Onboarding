"""
onboarding/schemas.py
---------------------
Pydantic schemas for API validation and response serialization.
"""

from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List
from datetime import datetime
import re
from app.onboarding_doctors.models import (
    Source, Status, SyncStatus,
    LocationPriority, FacilityType, LocationSource,
)


# ---------------------------------------------------------------------------
# Nested models
# ---------------------------------------------------------------------------

class LocationRequest(BaseModel):
    location_priority:   LocationPriority = Field(description="REQUIRED. Allowed: PRIMARY, SECONDARY, OTHER. Exactly one PRIMARY required; at most one SECONDARY.")
    facility_type:       FacilityType     = Field(description="REQUIRED. Allowed: HOSPITAL, CLINIC, POLYCLINIC, MEDICAL_CENTER, 'INSTITUTION OR MEDICAL COLLEGE', OTHER.")
    facility_type_other: Optional[str]    = Field(default=None, description="Optional. Free text — required only when facility_type is OTHER.")
    location_name:       str              = Field(description="REQUIRED. Institution name (hospital / clinic / college / etc.).")
    latitude:            Optional[str]    = Field(default=None, description="Optional. GPS latitude as a string, e.g. '17.385044'.")
    longitude:           Optional[str]    = Field(default=None, description="Optional. GPS longitude as a string, e.g. '78.486671'.")
    address:             Optional[str]    = Field(default=None, description="Optional. Full address string.")
    area:                Optional[str]    = Field(default=None, description="Optional. Locality / area within the city.")
    city:                str              = Field(description="REQUIRED. City.")
    district:            str              = Field(description="REQUIRED. District.")
    state:               str              = Field(description="REQUIRED. State or province.")
    country:             str              = Field(description="REQUIRED. Country.")
    postcode:            str              = Field(description="REQUIRED. Postal / ZIP code.")
    location_source:     Optional[LocationSource] = Field(default=None, description="Optional. Allowed: CURRENT_LOCATION, MAP_SEARCH, MANUAL.")

    model_config = {
        "json_schema_extra": {
            "example": {
                "location_priority": "PRIMARY",
                "facility_type":     "HOSPITAL",
                "location_name":     "Apollo Hospital",
                "latitude":          "17.385044",
                "longitude":         "78.486671",
                "address":           "Apollo Hospital, Jubilee Hills, Hyderabad",
                "area":              "Jubilee Hills",
                "city":              "Hyderabad",
                "district":          "Hyderabad",
                "state":             "Telangana",
                "country":           "India",
                "postcode":          "500033",
                "location_source":   "MAP_SEARCH",
            }
        }
    }


class LocationResponse(BaseModel):
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


# ---------------------------------------------------------------------------
# Request
# ---------------------------------------------------------------------------

class RegisterDoctorRequest(BaseModel):
    """
    Payload submitted by the frontend after the doctor reviews the form.
    Works for both VOICE and MANUAL registration.

    Voice session fields (transcript, ner_output, etc.) are optional.
    The frontend should include them when source=VOICE so the session
    audit trail captures the full pipeline data.
    """
    doctor_name:    str           = Field(description="Doctor's full name (title stripped)", min_length=8)
    username:       str           = Field(description="Doctor's chosen username for login")
    password:       str           = Field(description="Doctor's chosen password (8-64 chars, uppercase+lowercase+number+symbol)", min_length=8, max_length=64)

    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        if not re.match(r'^[A-Za-z0-9!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>\/?`~]+$', v):
            raise ValueError("Only English letters, numbers, and standard symbols are allowed")
        if not re.search(r'[A-Z]', v):
            raise ValueError("Password must include at least one uppercase letter")
        if not re.search(r'[a-z]', v):
            raise ValueError("Password must include at least one lowercase letter")
        if not re.search(r'[0-9]', v):
            raise ValueError("Password must include at least one number")
        if not re.search(r'[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>\/?`~]', v):
            raise ValueError("Password must include at least one symbol")
        return v
    email:          str           = Field(description="Email address")
    phone:          str           = Field(description="Phone number (exactly 10 digits)")
    specialization: str           = Field(description="Medical specialization. Accepts a value from GET /dobodb/api/specializations OR any manual/custom free-text value the frontend sends.")
    source:         Source        = Field(description="VOICE or MANUAL")
    locations:      List[LocationRequest] = Field(description="Doctor's practice locations (exactly one PRIMARY required)", min_length=1)

    # --- Voice session data (optional, sent by frontend for VOICE registrations) ---
    transcript:      Optional[str]  = Field(default=None, description="Raw transcript from STT")
    ner_output:      Optional[dict] = Field(default=None, description="Raw NER entities from pipeline")
    pipeline_output: Optional[dict] = Field(default=None, description="Full pipeline output (resolved values)")
    auto_fill:       Optional[dict] = Field(default=None, description="What was auto-filled into the form")
    corrections:     Optional[dict] = Field(default=None, description="What the doctor changed from auto-fill")

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v):
        cleaned = v.strip()
        # Allow +91 prefix — strip it
        if cleaned.startswith("+91"):
            cleaned = cleaned[3:].lstrip("-").strip()
        elif cleaned.startswith("+"):
            raise ValueError("Only Indian phone numbers (+91) are accepted")
        # Now we should have just digits (maybe with spaces/dashes)
        digits = re.sub(r"[\s\-]", "", cleaned)
        if not digits.isdigit():
            raise ValueError("Phone number must contain only digits")
        if len(digits) != 10:
            raise ValueError("Phone number must be exactly 10 digits (with optional +91 prefix)")
        return f"+91{digits}"

    @field_validator("locations")
    @classmethod
    def validate_locations(cls, v):
        primary   = sum(1 for loc in v if loc.location_priority == LocationPriority.PRIMARY)
        secondary = sum(1 for loc in v if loc.location_priority == LocationPriority.SECONDARY)
        if primary != 1:
            raise ValueError(f"Exactly one PRIMARY location is required (found {primary})")
        if secondary > 1:
            raise ValueError(f"At most one SECONDARY location is allowed (found {secondary})")
        return v


    model_config = {
        "json_schema_extra": {
            "example": {
                "doctor_name":    "Rahul Sharma",
                "username":       "rahul_sharma",
                "password":       "Rahul@123",
                "email":          "rahul@gmail.com",
                "phone":          "+919876543210",
                "specialization": "Cardiology",
                "source":         "VOICE",
                "locations": [
                    {
                        "location_priority": "PRIMARY",
                        "facility_type":     "HOSPITAL",
                        "location_name":     "Apollo Hospital",
                        "latitude":          "17.385044",
                        "longitude":         "78.486671",
                        "address":           "Apollo Hospital, Jubilee Hills, Hyderabad",
                        "area":              "Jubilee Hills",
                        "city":              "Hyderabad",
                        "district":          "Hyderabad",
                        "state":             "Telangana",
                        "country":           "India",
                        "postcode":          "500033",
                        "location_source":   "MAP_SEARCH",
                    }
                ],
                "transcript": "I am Dr Rahul Sharma from Apollo Hospital Cardiology department",
                "ner_output": {
                    "DOCTOR_NAME": ["Dr Rahul Sharma"],
                    "HOSPITAL": ["Apollo Hospital"],
                    "SPECIALIZATION": ["Cardiology"],
                },
                "pipeline_output": {
                    "doctor_name": "Rahul Sharma",
                    "hospital": "Apollo Hospital",
                    "specialization": "Cardiology",
                    "phone": "",
                    "email": "",
                },
                "auto_fill": {
                    "doctor_name": "Rahul Sharma",
                    "hospital": "Apollo Hospital",
                    "specialization": "Cardiology",
                },
                "corrections": {
                    "email": {"from": "", "to": "rahul@gmail.com"},
                    "phone": {"from": "", "to": "+919876543210"},
                },
            }
        }
    }


# ---------------------------------------------------------------------------
# Response
# ---------------------------------------------------------------------------

class RegisterDoctorResponse(BaseModel):
    """
    Returned after successful doctor registration.
    onboarding_id is MongoDB's _id as a string — identifies this onboarding record.
    """
    onboarding_id:  str                    = Field(description="MongoDB ObjectId of this onboarding record")
    doctor_name:    str
    username:       str
    email:          Optional[str]          = None
    phone:          Optional[str]          = None
    specialization: Optional[str]          = None
    source:         Source
    status:         Status
    sync_status:    SyncStatus
    sync_error:     Optional[str]          = Field(default=None, description="Error message if sync to DRX failed")
    locations:      List[LocationResponse] = Field(default_factory=list)
    created_at:     datetime

    model_config = {
        "json_schema_extra": {
            "example": {
                "onboarding_id":  "64f1a2b3c4d5e6f7a8b9c0d1",
                "doctor_name":    "Rahul Sharma",
                "username":       "rahul_sharma",
                "email":          "rahul@gmail.com",
                "phone":          "+919876543210",
                "specialization": "Cardiology",
                "source":         "VOICE",
                "status":         "ACTIVE",
                "sync_status":    "SYNCED",
                "sync_error":     None,
                "locations": [
                    {
                        "location_priority": "PRIMARY",
                        "facility_type":     "HOSPITAL",
                        "location_name":     "Apollo Hospital",
                        "area":              "Jubilee Hills",
                        "city":              "Hyderabad",
                        "district":          "Hyderabad",
                        "state":             "Telangana",
                        "country":           "India",
                        "postcode":          "500033",
                        "status":            "ACTIVE",
                    }
                ],
                "created_at": "2026-08-05T10:30:00Z",
            }
        }
    }


class DoctorListItem(BaseModel):
    """Single doctor item in the list response."""
    onboarding_id:  str
    doctor_name:    str
    username:       str
    email:          Optional[str] = None
    phone:          Optional[str] = None
    specialization: Optional[str] = None
    source:         Source
    status:         Status
    sync_status:    SyncStatus
    sync_error:     Optional[str] = None
    locations:      List[LocationResponse] = Field(default_factory=list)
    created_at:     datetime


class DoctorListResponse(BaseModel):
    """Paginated list of onboarded doctors."""
    total:   int                    = Field(description="Total number of doctors matching the filter")
    page:    int                    = Field(description="Current page number")
    limit:   int                    = Field(description="Number of items per page")
    doctors: List[DoctorListItem]   = Field(description="List of doctors")
