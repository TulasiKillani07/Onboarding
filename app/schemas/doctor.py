"""
Pydantic schemas for doctor registration data.
Includes full OpenAPI documentation for Swagger UI.
"""

from pydantic import BaseModel, Field
from typing import Optional


# ---------------------------------------------------------------------------
# Core data models
# ---------------------------------------------------------------------------

class DoctorRegistration(BaseModel):
    """Resolved doctor registration data — one value per field."""
    name:       str = Field(default="", description="Full name of the doctor without title (e.g. 'Tulasi Killani')")
    email:      str = Field(default="", description="Email address (e.g. 'tulasi@gmail.com')")
    phone:      str = Field(default="", description="Phone number (e.g. '9876543210')")
    hospital:   str = Field(default="", description="Hospital or clinic name (e.g. 'Apollo Hospital')")
    department: str = Field(default="", description="Medical specialization (e.g. 'Dermatology')")

    model_config = {
        "json_schema_extra": {
            "example": {
                "name":       "Tulasi Killani",
                "email":      "tulasi@gmail.com",
                "phone":      "9876543210",
                "hospital":   "Apollo Hospital",
                "department": "Dermatology",
            }
        }
    }


class RawEntities(BaseModel):
    """Multi-value raw entities before resolution — for debugging."""
    DOCTOR_NAME:    list = Field(default=[], description="All detected doctor name spans")
    HOSPITAL:       list = Field(default=[], description="All detected hospital spans")
    SPECIALIZATION: list = Field(default=[], description="All detected specialization spans")
    PHONE:          list = Field(default=[], description="All detected phone numbers")
    EMAIL:          list = Field(default=[], description="All detected email addresses")


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class TranscriptInput(BaseModel):
    """Text transcript input for the /extract endpoint."""
    transcript: str = Field(
        description="Plain text transcript from the doctor. Can be typed or speech-to-text output.",
        min_length=3,
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "transcript": "Hi I am Dr Tulasi Killani. I work at Apollo Hospital. I am a dermatologist. My number is 9876543210. Email: tulasi@gmail.com"
            }
        }
    }


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class TranscriptionResponse(BaseModel):
    """Response from POST /api/voice/transcribe"""
    success:    bool                  = Field(description="True if transcription succeeded")
    transcript: str                   = Field(description="Transcribed text from the audio")
    language:   Optional[str]         = Field(default="en", description="Detected language code")
    duration:   Optional[float]       = Field(default=None, description="Audio duration in seconds")

    model_config = {
        "json_schema_extra": {
            "example": {
                "success":    True,
                "transcript": "Hi I am Dr Tulasi Killani working at Apollo Hospital. I am a dermatologist.",
                "language":   "en",
                "duration":   4.2,
            }
        }
    }


class ExtractionResponse(BaseModel):
    """Response from POST /api/voice/extract and POST /api/voice/process"""
    success:        bool                  = Field(description="True if extraction succeeded")
    data:           DoctorRegistration    = Field(description="Resolved registration data — one value per field")
    transcript:     Optional[str]         = Field(default="", description="Original transcript text")
    entities:       Optional[dict]        = Field(default={}, description="Raw multi-value entities (for debugging)")
    confidence:     Optional[float]       = Field(default=0.0, description="Confidence score 0.0–1.0 based on filled fields")
    pipeline_steps: Optional[list]        = Field(default=[], description="Debug info from each pipeline stage")

    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "data": {
                    "name":       "Tulasi Killani",
                    "email":      "tulasi@gmail.com",
                    "phone":      "9876543210",
                    "hospital":   "Apollo Hospital",
                    "department": "Dermatology",
                },
                "transcript": "Hi I am Dr Tulasi Killani working at Apollo Hospital. I am a dermatologist.",
                "entities": {
                    "DOCTOR_NAME":    [{"text": "Tulasi Killani", "start": 14, "end": 28}],
                    "HOSPITAL":       [{"text": "Apollo Hospital", "start": 40, "end": 55}],
                    "SPECIALIZATION": [{"text": "Dermatology", "start": 64, "end": 75}],
                    "PHONE":          [{"text": "9876543210", "start": 89, "end": 99}],
                    "EMAIL":          [{"text": "tulasi@gmail.com", "start": 108, "end": 124}],
                },
                "confidence": 1.0,
                "pipeline_steps": [
                    {"step": "transcription", "result": {"duration": 4.2}},
                    {"step": "ner_pipeline", "result": {"doctor_name": "Tulasi Killani"}},
                ],
            }
        }
    }


class SpecializationListResponse(BaseModel):
    """Response from GET /api/specializations"""
    top:     list[str] = Field(description="Top 10 most common specializations (show first in dropdown)")
    all:     list[str] = Field(description="Complete canonical specialization list")
    ordered: list[str] = Field(description="Top 10 first, then rest alphabetically — use this for dropdown")
    total:   int       = Field(description="Total number of specializations in the master list")

    model_config = {
        "json_schema_extra": {
            "example": {
                "top":     ["General Physician", "Cardiology", "Dermatology"],
                "all":     ["General Physician", "Cardiology", "Dermatology", "Neurology"],
                "ordered": ["General Physician", "Cardiology", "Dermatology", "Neurology"],
                "total":   62,
            }
        }
    }
