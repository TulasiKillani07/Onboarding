"""
onboarding/schemas.py
---------------------
Pydantic schemas for API validation and response serialization.
"""

from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List
from datetime import datetime
import re
from app.onboarding_doctors.models import Source, Status, SyncStatus


# ---------------------------------------------------------------------------
# Nested models
# ---------------------------------------------------------------------------

class LocationRequest(BaseModel):
    latitude:  Optional[str] = Field(default=None, description="GPS latitude")
    longitude: Optional[str] = Field(default=None, description="GPS longitude")
    address:   Optional[str] = Field(default=None, description="Full address string")
    city:      Optional[str] = Field(default=None, description="City")
    state:     Optional[str] = Field(default=None, description="State or province")
    country:   Optional[str] = Field(default=None, description="Country")

    model_config = {
        "json_schema_extra": {
            "example": {
                "latitude":  "17.385044",
                "longitude": "78.486671",
                "address":   "Apollo Hospital, Jubilee Hills, Hyderabad",
                "city":      "Hyderabad",
                "state":     "Telangana",
                "country":   "India",
            }
        }
    }


class LocationResponse(BaseModel):
    latitude:  Optional[str] = None
    longitude: Optional[str] = None
    address:   Optional[str] = None
    city:      Optional[str] = None
    state:     Optional[str] = None
    country:   Optional[str] = None


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
    hospital:       str           = Field(description="Hospital or clinic name")
    specialization: str           = Field(description="Medical specialization")
    source:         Source        = Field(description="VOICE or MANUAL")
    location:       LocationRequest = Field(description="Doctor's location")

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

    model_config = {
        "json_schema_extra": {
            "example": {
                "doctor_name":    "Rahul Sharma",
                "username":       "rahul_sharma",
                "password":       "Rahul@123",
                "email":          "rahul@gmail.com",
                "phone":          "+919876543210",
                "hospital":       "Apollo Hospital",
                "specialization": "Cardiology",
                "source":         "VOICE",
                "location": {
                    "latitude":  "17.385044",
                    "longitude": "78.486671",
                    "address":   "Apollo Hospital, Jubilee Hills, Hyderabad",
                    "city":      "Hyderabad",
                    "state":     "Telangana",
                    "country":   "India",
                },
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
    onboarding_id is MongoDB's _id as a string â€” identifies this onboarding record.
    drx_doctor_gid is null until DRX sync completes.
    """
    onboarding_id:  str                    = Field(description="MongoDB ObjectId of this onboarding record")
    doctor_name:    str
    username:       str
    email:          Optional[str]          = None
    phone:          Optional[str]          = None
    hospital:       Optional[str]          = None
    specialization: Optional[str]          = None
    source:         Source
    status:         Status
    sync_status:    SyncStatus
    sync_error:     Optional[str]          = Field(default=None, description="Error message if sync to DRX failed")
    location:       Optional[LocationResponse] = None
    created_at:     datetime

    model_config = {
        "json_schema_extra": {
            "example": {
                "onboarding_id":  "64f1a2b3c4d5e6f7a8b9c0d1",
                "doctor_name":    "Rahul Sharma",
                "username":       "rahul_sharma",
                "email":          "rahul@gmail.com",
                "phone":          "+919876543210",
                "hospital":       "Apollo Hospital",
                "specialization": "Cardiology",
                "source":         "VOICE",
                "status":         "ACTIVE",
                "sync_status":    "SYNCED",
                "sync_error":     None,
                "location": {
                    "city":    "Hyderabad",
                    "state":   "Telangana",
                    "country": "India",
                },
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
    hospital:       Optional[str] = None
    specialization: Optional[str] = None
    source:         Source
    status:         Status
    sync_status:    SyncStatus
    sync_error:     Optional[str] = None
    location:       Optional[LocationResponse] = None
    created_at:     datetime


class DoctorListResponse(BaseModel):
    """Paginated list of onboarded doctors."""
    total:   int                    = Field(description="Total number of doctors matching the filter")
    page:    int                    = Field(description="Current page number")
    limit:   int                    = Field(description="Number of items per page")
    doctors: List[DoctorListItem]   = Field(description="List of doctors")
