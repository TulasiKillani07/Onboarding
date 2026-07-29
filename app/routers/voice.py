"""
Voice registration API endpoints.
Handles audio upload, transcription, and entity extraction pipeline.
"""

from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel

from app.schemas.doctor import TranscriptionResponse, ExtractionResponse, DoctorRegistration
from app.services.whisper_service import WhisperService
from app.services.regex_service import RegexService
from app.services.ner_service import NERService
from app.services.llm_service import LLMService

router = APIRouter()


class TranscriptInput(BaseModel):
    """Input for extraction endpoint."""
    transcript: str


@router.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_audio(file: UploadFile = File(...)):
    """
    Transcribe audio file to text using Faster-Whisper.

    Accepts audio files (WAV, MP3, WebM, OGG) and returns the transcript.
    """
    # Validate file type
    allowed_types = [
        "audio/wav", "audio/wave", "audio/x-wav",
        "audio/mp3", "audio/mpeg",
        "audio/webm", "audio/ogg",
        "video/webm",  # Some browsers report webm as video
    ]

    # Be lenient with content type checking
    content_type = file.content_type or ""
    if content_type and content_type not in allowed_types:
        # Still allow if extension is valid
        valid_extensions = [".wav", ".mp3", ".webm", ".ogg", ".m4a"]
        filename = file.filename or ""
        if not any(filename.lower().endswith(ext) for ext in valid_extensions):
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported audio format: {content_type}. Supported: WAV, MP3, WebM, OGG"
            )

    try:
        # Read audio bytes
        audio_bytes = await file.read()

        if len(audio_bytes) == 0:
            raise HTTPException(status_code=400, detail="Empty audio file")

        # Transcribe
        whisper = WhisperService.get_instance()
        transcript, duration = await whisper.transcribe(audio_bytes, file.filename or "audio.wav")

        if not transcript.strip():
            return TranscriptionResponse(
                success=False,
                transcript="",
                duration=duration,
            )

        return TranscriptionResponse(
            success=True,
            transcript=transcript.strip(),
            language="en",
            duration=duration,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")


@router.post("/extract", response_model=ExtractionResponse)
async def extract_entities(input_data: TranscriptInput):
    """
    Extract doctor registration data from transcript.

    Pipeline: Transcript → Regex → spaCy NER → Gemini Flash → Validated JSON
    """
    transcript = input_data.transcript

    if not transcript.strip():
        raise HTTPException(status_code=400, detail="Empty transcript")

    pipeline_steps = []

    try:
        # Step 1: Regex extraction (phone, email)
        regex_data = RegexService.extract_all(transcript)
        pipeline_steps.append({
            "step": "regex",
            "result": regex_data,
        })

        # Step 2: spaCy NER (name, hospital, department)
        ner_service = NERService.get_instance()
        ner_data = ner_service.extract_entities(transcript)
        pipeline_steps.append({
            "step": "ner",
            "result": ner_data,
        })

        # Step 3: LLM validation and normalization
        llm_service = LLMService.get_instance()
        validated_data = await llm_service.validate_and_normalize(
            transcript, regex_data, ner_data
        )
        pipeline_steps.append({
            "step": "llm_validation",
            "result": validated_data,
        })

        # Build response
        doctor_data = DoctorRegistration(
            name=validated_data.get("name", ""),
            email=validated_data.get("email", ""),
            phone=validated_data.get("phone", ""),
            hospital=validated_data.get("hospital", ""),
            department=validated_data.get("department", ""),
        )

        # Calculate confidence (simple heuristic)
        filled_fields = sum(1 for v in validated_data.values() if v)
        confidence = filled_fields / 5.0  # 5 total fields

        return ExtractionResponse(
            success=True,
            data=doctor_data,
            transcript=transcript,
            entities=ner_data,
            confidence=confidence,
            pipeline_steps=pipeline_steps,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")


@router.post("/process", response_model=ExtractionResponse)
async def process_audio(file: UploadFile = File(...)):
    """
    Full pipeline: Audio → Transcription → Extraction → Validated JSON.
    Combines transcribe and extract into a single endpoint.
    """
    # Step 1: Transcribe
    allowed_types = [
        "audio/wav", "audio/wave", "audio/x-wav",
        "audio/mp3", "audio/mpeg",
        "audio/webm", "audio/ogg",
        "video/webm",
    ]

    try:
        audio_bytes = await file.read()
        if len(audio_bytes) == 0:
            raise HTTPException(status_code=400, detail="Empty audio file")

        whisper = WhisperService.get_instance()
        transcript, duration = await whisper.transcribe(audio_bytes, file.filename or "audio.wav")

        if not transcript.strip():
            raise HTTPException(status_code=400, detail="Could not transcribe audio. Please try again.")

        # Step 2: Extract
        regex_data = RegexService.extract_all(transcript)
        ner_service = NERService.get_instance()
        ner_data = ner_service.extract_entities(transcript)

        # Step 3: LLM validation
        llm_service = LLMService.get_instance()
        validated_data = await llm_service.validate_and_normalize(
            transcript, regex_data, ner_data
        )

        doctor_data = DoctorRegistration(
            name=validated_data.get("name", ""),
            email=validated_data.get("email", ""),
            phone=validated_data.get("phone", ""),
            hospital=validated_data.get("hospital", ""),
            department=validated_data.get("department", ""),
        )

        filled_fields = sum(1 for v in validated_data.values() if v)
        confidence = filled_fields / 5.0

        return ExtractionResponse(
            success=True,
            data=doctor_data,
            transcript=transcript,
            entities=ner_data,
            confidence=confidence,
            pipeline_steps=[
                {"step": "transcription", "result": {"transcript": transcript, "duration": duration}},
                {"step": "regex", "result": regex_data},
                {"step": "ner", "result": ner_data},
                {"step": "llm_validation", "result": validated_data},
            ],
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")
