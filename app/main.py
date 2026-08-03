"""
DRX Doctor Registration - FastAPI Backend
AI-powered doctor registration pipeline:
Audio → Faster-Whisper → Regex → spaCy NER → Gemini Flash → Validated JSON
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import voice, specializations

app = FastAPI(
    title="DRX Doctor Registration API",
    description="AI-powered doctor registration pipeline for DRX platform",
    version="1.0.0",
)

# CORS configuration for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(voice.router, prefix="/api/voice", tags=["Voice Registration"])
app.include_router(specializations.router, prefix="/api/specializations", tags=["Specializations"])


@app.get("/", tags=["Health"])
async def root():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "DRX Doctor Registration API",
        "version": "1.0.0",
    }


@app.get("/api/health", tags=["Health"])
async def health_check():
    """Detailed health check."""
    return {
        "status": "healthy",
        "services": {
            "whisper": "ready",
            "spacy": "ready",
            "gemini": "configured",
        },
    }
