"""
Pydantic schemas for doctor registration data.
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional


class LocationData(BaseModel):
    """Location information for a doctor's practice."""
    latitude: Optional[str] = ""
    longitude: Optional[str] = ""
    address: Optional[str] = ""
    city: Optional[str] = ""
    state: Optional[str] = ""
    country: Optional[str] = ""


class DoctorRegistration(BaseModel):
    """Complete doctor registration data."""
    name: str = Field(default="", description="Full name of the doctor")
    email: str = Field(default="", description="Email address")
    phone: str = Field(default="", description="Phone number")
    hospital: str = Field(default="", description="Hospital or clinic name")
    department: str = Field(default="", description="Department or specialization")
    location: Optional[LocationData] = LocationData()


class TranscriptionResponse(BaseModel):
    """Response from the transcription endpoint."""
    success: bool
    transcript: str
    language: Optional[str] = "en"
    duration: Optional[float] = None


class ExtractionResponse(BaseModel):
    """Response from the extraction endpoint."""
    success: bool
    data: DoctorRegistration
    transcript: Optional[str] = ""
    entities: Optional[dict] = {}
    confidence: Optional[float] = 0.0
    pipeline_steps: Optional[list] = []
