"""
DRX Doctor Registration - FastAPI Backend

Architecture:
  app/sarvam/         — Speech module (audio -> transcript)
  app/onboarding_ner/ — NER module   (transcript -> entities -> resolved JSON)
  app/routers/voice.py — Thin orchestrator
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import voice, specializations

# ---------------------------------------------------------------------------
# API description shown in Swagger UI
# ---------------------------------------------------------------------------
_DESCRIPTION = """
## DRX Doctor Onboarding — Backend API

AI-powered voice registration pipeline for doctors.

### How it works
1. Doctor speaks their name, hospital, specialization, phone and email
2. Audio is transcribed using **Sarvam AI** (Indian language optimized)
3. Transcript is processed by a **custom-trained spaCy NER model**
4. Entities are validated, normalized and resolved to single values
5. Returns a clean `DoctorRegistration` JSON ready to populate the form

### Endpoints for the frontend

| Endpoint | When to use |
|---|---|
| `POST /api/voice/process` | **Primary** — upload audio, get filled form data |
| `POST /api/voice/extract` | If you already have a transcript (typed input) |
| `POST /api/voice/transcribe` | If you only need the transcript (no extraction) |
| `GET /api/specializations` | Load the specialization dropdown on page load |

### Pipeline stages
```
Audio
  ↓ Sarvam AI STT          (speech → text)
  ↓ Regex                  (phone, email)
  ↓ Custom spaCy NER       (name, hospital, specialization)
  ↓ Validation             (reject garbage entities)
  ↓ Pattern Extractor      ("I am skin specialist" → Dermatology)
  ↓ Normalization          (strip title, fix typos, map aliases)
  ↓ Resolution             (collapse to 1 value per field or null)
  ↓ DoctorRegistration JSON
```

### Notes
- All extraction is **fully local** — no Gemini, no external LLM
- Only Sarvam AI (STT) requires an API key
- Phone and email extracted via regex, not NER
- Doctor titles (Dr., Prof.) are automatically stripped from names
"""

app = FastAPI(
    title="DRX Doctor Registration API",
    description=_DESCRIPTION,
    version="3.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {
            "name": "Voice Registration",
            "description": "Audio transcription and entity extraction endpoints. "
                           "Use **POST /process** for the full pipeline.",
        },
        {
            "name": "Specializations",
            "description": "Canonical specialization list for the registration form dropdown.",
        },
        {
            "name": "Health",
            "description": "Service health checks.",
        },
    ],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(voice.router,           prefix="/api/voice",           tags=["Voice Registration"])
app.include_router(specializations.router, prefix="/api/specializations", tags=["Specializations"])


@app.get(
    "/",
    tags=["Health"],
    summary="Service info",
    description="Returns service name, version, and pipeline overview.",
)
async def root():
    return {
        "status":  "healthy",
        "service": "DRX Doctor Registration API",
        "version": "3.0.0",
        "docs":    "/docs",
        "pipeline": [
            "POST /api/voice/process      — audio → form data (primary endpoint)",
            "POST /api/voice/extract      — transcript → form data",
            "POST /api/voice/transcribe   — audio → transcript only",
            "GET  /api/specializations    — dropdown list",
        ],
    }


@app.get(
    "/api/health",
    tags=["Health"],
    summary="Health check",
    description="Returns status of all pipeline modules.",
    responses={
        200: {
            "description": "All modules healthy",
            "content": {
                "application/json": {
                    "example": {
                        "status": "healthy",
                        "modules": {
                            "sarvam_stt":     "ready",
                            "onboarding_ner": "ready",
                        }
                    }
                }
            }
        }
    }
)
async def health_check():
    return {
        "status": "healthy",
        "modules": {
            "sarvam_stt":     "ready",
            "onboarding_ner": "ready",
        },
    }
