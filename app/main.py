"""
DRX Doctor Registration - FastAPI Backend

Feature-based structure:
  app/voice/              — voice extraction (STT + NER)
  app/onboarding_doctors/ — doctor registration (save to DB)
  app/specializations/    — specialization dropdown
  app/database.py         — MongoDB connection
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import DatabaseClient, initialize_database
from app.voice import router as voice_router
from app.onboarding_doctors import router as onboarding_router
from app.specializations import router as specializations_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    DatabaseClient.connect()
    await initialize_database()
    yield
    DatabaseClient.disconnect()


app = FastAPI(
    title="DRX Doctor Registration API",
    version="3.0.0",
    lifespan=lifespan,
    docs_url="/docs",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(voice_router,           prefix="/api/voice",           tags=["Voice"])
app.include_router(onboarding_router,      prefix="/api/onboarding",      tags=["Onboarding Doctors"])
app.include_router(specializations_router, prefix="/api/specializations", tags=["Specializations"])


@app.get("/", tags=["Health"])
async def root():
    return {"status": "healthy", "service": "DRX Doctor Registration API", "version": "3.0.0"}


@app.get("/api/health", tags=["Health"])
async def health_check():
    from fastapi.responses import JSONResponse
    db_ok = await DatabaseClient.ping()
    return JSONResponse(
        content={"status": "healthy" if db_ok else "unhealthy", "api": "running", "database": "connected" if db_ok else "disconnected"},
        status_code=200 if db_ok else 503,
    )
