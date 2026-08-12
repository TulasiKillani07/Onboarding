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
from app.utils.logger import setup_logging, get_dobo_logger
from app.database import DatabaseClient, initialize_database
from app.http_client import HttpClient
from app.voice import router as voice_router
from app.voice.ner import load_model as load_ner_model
from app.onboarding_doctors import router as onboarding_router
from app.specializations import router as specializations_router

logger = get_dobo_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize logging FIRST (before anything else logs)
    setup_logging()
    logger.info("Application starting...")
    # Load NER model once at startup (not per-request)
    load_ner_model()
    # Start shared HTTP client (connection pooling for Sarvam + DRX)
    HttpClient.start()
    # Connect to MongoDB
    DatabaseClient.connect()
    await initialize_database()
    logger.info("Application ready")
    yield
    logger.info("Application shutting down...")
    await HttpClient.stop()
    DatabaseClient.disconnect()
    logger.info("Application stopped")


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
