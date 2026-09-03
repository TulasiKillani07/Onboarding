"""
Voice Router - thin orchestrator.

Dependency flow:
    voice.py
        -> SarvamService.transcribe(audio) -> transcript (str)
        -> OnboardingNER.process(transcript) -> resolved dict

The two modules (sarvam/ and onboarding_ner/) are fully independent.
"""

import asyncio
from fastapi import APIRouter, UploadFile, File, HTTPException, status
from app.voice.schemas import TranscriptInput, TranscriptionResponse, ExtractionResponse, DoctorRegistration
from app.voice.sarvam import SarvamService
from app.voice.ner import OnboardingNER
from app.utils.logger import get_dobo_logger

logger = get_dobo_logger(__name__)

router = APIRouter()

_ALLOWED_AUDIO_TYPES = {
    "audio/wav", "audio/wave", "audio/x-wav",
    "audio/mp3", "audio/mpeg",
    "audio/webm", "audio/ogg",
    "video/webm",
}
_ALLOWED_EXTENSIONS = {".wav", ".mp3", ".webm", ".ogg", ".m4a"}


def _validate_audio(file: UploadFile):
    ct = file.content_type or ""
    if ct and ct not in _ALLOWED_AUDIO_TYPES:
        fn = file.filename or ""
        if not any(fn.lower().endswith(ext) for ext in _ALLOWED_EXTENSIONS):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported format: {ct}. Accepted: WAV, MP3, WebM, OGG",
            )


def _build_response(resolved: dict, transcript: str,
                    entities: dict, extra_steps: list | None = None) -> ExtractionResponse:
    doctor_data = DoctorRegistration(
        name=resolved.get("doctor_name") or "",
        email=resolved.get("email") or "",
        phone=resolved.get("phone") or "",
        hospital=resolved.get("hospital") or "",
        department=resolved.get("specialization") or "",
    )
    filled = sum(1 for k, v in resolved.items() if k != "entities" and v)
    steps  = (extra_steps or []) + [{"step": "ner_pipeline", "result": {k: v for k, v in resolved.items() if k != "entities"}}]
    return ExtractionResponse(
        success=True,
        data=doctor_data,
        transcript=transcript,
        entities=entities,
        confidence=round(filled / 5.0, 2),
        pipeline_steps=steps,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/transcribe",
    response_model=TranscriptionResponse,
    summary="Transcribe audio to text (STT only)",
    description="""
Upload an audio file and get the raw transcript back. **No entity extraction** is performed.

### Input
- `file` — multipart audio upload. Supported: **WAV, MP3, WebM, OGG, M4A**. Keep under ~30s.

### Pipeline
`Audio → Sarvam AI Saaras v3 STT → Transcript`

### When to use
Use this when the frontend just needs the spoken text (e.g. to display it), and will call
`/extract` separately. For the full one-shot flow, use `/process` instead.

### Response
Returns `success`, the `transcript`, detected `language`, and audio `duration`.
If no speech is detected, `success=false` with an empty transcript.
""",
    responses={
        200: {"description": "Transcription completed (check `success` flag)"},
        400: {"description": "Empty file or unsupported audio format"},
        500: {"description": "Sarvam STT API error"},
    },
)
async def transcribe_audio(
    file: UploadFile = File(..., description="Audio file (WAV/MP3/WebM/OGG). Max recommended: 30 seconds.")
):
    _validate_audio(file)
    logger.info(f"Transcribe request | filename={file.filename}")
    try:
        audio_bytes = await file.read()
        if not audio_bytes:
            raise HTTPException(status_code=400, detail="Empty audio file")
        transcript, duration = await SarvamService.get_instance().transcribe(
            audio_bytes, file.filename or "audio.wav"
        )
        if not transcript.strip():
            logger.warning("Transcription returned empty")
            return TranscriptionResponse(success=False, transcript="", duration=duration)
        logger.info(f"Transcription success | duration={duration:.1f}s len={len(transcript)}")
        return TranscriptionResponse(success=True, transcript=transcript.strip(),
                                     language="en", duration=duration)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Transcription failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")


@router.post(
    "/extract",
    response_model=ExtractionResponse,
    summary="Extract doctor fields from a transcript (NER only)",
    description="""
Extract structured doctor registration fields from a plain-text transcript.

### Input
JSON body with a single `transcript` string (typed text or pre-transcribed speech).

### Pipeline
`Transcript → Regex → NER → Validate → Pattern Extract → Normalize → Resolve`

### Fields returned (exactly one value each, empty string if not found)
| Field | Description |
|-------|-------------|
| `name` | Doctor's full name, title stripped (Dr., Prof. removed) |
| `hospital` | Institution / hospital / clinic name |
| `department` | Medical specialization |
| `phone` | Phone number |
| `email` | Email address |

### Confidence
`confidence` is `0.0–1.0`, computed as the fraction of the 5 fields successfully filled.

### When to use
Use this when you already have the transcript. To go straight from audio to fields,
use `/process`.
""",
    responses={
        200: {"description": "Extraction completed"},
        400: {"description": "Empty transcript"},
        500: {"description": "Internal extraction error"},
    },
)
async def extract_entities(
    input_data: TranscriptInput,
):
    if not input_data.transcript.strip():
        raise HTTPException(status_code=400, detail="Empty transcript")
    logger.info(f"Extract request | input_len={len(input_data.transcript)}")
    try:
        result = await asyncio.to_thread(OnboardingNER.process, input_data.transcript)
        filled = sum(1 for k, v in result.items() if k != "entities" and v)
        logger.info(f"Extract success | fields_filled={filled}")
        # Debug only: truncated transcript (no PII at INFO)
        logger.debug(f"Extract input (truncated): {input_data.transcript[:50]}...")
        return _build_response(result, input_data.transcript, result.get("entities", {}))
    except Exception as e:
        logger.error(f"Extraction failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")


@router.post(
    "/process",
    response_model=ExtractionResponse,
    summary="Full pipeline: audio → extracted doctor fields (primary endpoint)",
    description="""
Upload a voice recording and get fully extracted, normalized doctor registration fields
in a **single call**. This is the primary endpoint the registration form should use.

### Input
- `file` — multipart audio upload. Supported: **WAV, MP3, WebM, OGG, M4A**. Keep under ~30s.
- Ask the doctor to say: name, hospital/institution, specialization, phone, and email.

### Pipeline
1. `Audio → Sarvam AI STT → Transcript`
2. Regex extraction (phone, email)
3. Custom spaCy NER (name, hospital, specialization)
4. Validate — reject garbage entities
5. Pattern extract — catch informal terms
6. Normalize — strip titles, fix hospital typos, map specialization aliases
7. Resolve — collapse to exactly one value per field

### Output
Same shape as `/extract`: `data` with one value per field, plus `transcript`, raw
`entities`, `confidence`, and `pipeline_steps` for debugging. Missing fields come back
as empty strings — **never null** — so the form can bind safely.
""",
    responses={
        200: {"description": "Full pipeline succeeded"},
        400: {"description": "Empty file, unsupported format, or no speech detected"},
        500: {"description": "STT or NER pipeline error"},
    },
)
async def process_audio(
    file: UploadFile = File(..., description="Doctor's voice recording. Speak name, hospital, specialization, phone, and email.")
):
    _validate_audio(file)
    logger.info(f"Process request | filename={file.filename}")
    try:
        audio_bytes = await file.read()
        if not audio_bytes:
            raise HTTPException(status_code=400, detail="Empty audio file")
        transcript, duration = await SarvamService.get_instance().transcribe(
            audio_bytes, file.filename or "audio.wav"
        )
        if not transcript.strip():
            logger.warning("Process: no speech detected")
            raise HTTPException(status_code=400, detail="No speech detected. Please try again.")

        logger.info(f"STT complete | duration={duration:.1f}s len={len(transcript)}")
        # Debug only: truncated transcript
        logger.debug(f"Transcript (truncated): {transcript[:50]}...")

        result = await asyncio.to_thread(OnboardingNER.process, transcript)
        filled = sum(1 for k, v in result.items() if k != "entities" and v)
        logger.info(f"Process complete | fields_filled={filled} confidence={filled/5.0:.2f}")

        return _build_response(
            result, transcript, result.get("entities", {}),
            extra_steps=[{"step": "transcription", "result": {"transcript": transcript, "duration": duration}}],
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Processing failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")
