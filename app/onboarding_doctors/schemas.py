"""
onboarding/schemas.py
---------------------
Pydantic schemas for API validation and response serialization.
"""

from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional
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
    doctor_name:    str           = Field(description="Doctor's full name (title stripped)")
    email:          Optional[str] = Field(default=None, description="Email address")
    phone:          Optional[str] = Field(default=None, description="Phone number")
    hospital:       Optional[str] = Field(default=None, description="Hospital or clinic name")
    specialization: Optional[str] = Field(default=None, description="Medical specialization")
    source:         Source        = Field(description="VOICE or MANUAL")
    location:       Optional[LocationRequest] = Field(default=None)

    # --- Voice session data (optional, sent by frontend for VOICE registrations) ---
    transcript:      Optional[str]  = Field(default=None, description="Raw transcript from STT")
    ner_output:      Optional[dict] = Field(default=None, description="Raw NER entities from pipeline")
    pipeline_output: Optional[dict] = Field(default=None, description="Full pipeline output (resolved values)")
    auto_fill:       Optional[dict] = Field(default=None, description="What was auto-filled into the form")
    corrections:     Optional[dict] = Field(default=None, description="What the doctor changed from auto-fill")

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v):
        if v is None:
            return v
        digits = re.sub(r"\D", "", v)
        if len(digits) != 10:
            raise ValueError("Phone number must be exactly 10 digits")
        return digits

    model_config = {
        "json_schema_extra": {
            "example": {
                "doctor_name":    "Rahul Sharma",
                "email":          "rahul@gmail.com",
                "phone":          "9876543210",
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
                    "phone": {"from": "", "to": "9876543210"},
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
    email:          Optional[str]          = None
    phone:          Optional[str]          = None
    hospital:       Optional[str]          = None
    specialization: Optional[str]          = None
    source:         Source
    status:         Status
    sync_status:    SyncStatus
    location:       Optional[LocationResponse] = None
    created_at:     datetime

    model_config = {
        "json_schema_extra": {
            "example": {
                "onboarding_id":  "64f1a2b3c4d5e6f7a8b9c0d1",
                "doctor_name":    "Rahul Sharma",
                "email":          "rahul@gmail.com",
                "phone":          "9876543210",
                "hospital":       "Apollo Hospital",
                "specialization": "Cardiology",
                "source":         "VOICE",
                "status":         "ACTIVE",
                "sync_status":    "PENDING",
                "drx_doctor_gid": None,
                "location": {
                    "city":    "Hyderabad",
                    "state":   "Telangana",
                    "country": "India",
                },
                "created_at": "2026-08-05T10:30:00Z",
            }
        }
    }


