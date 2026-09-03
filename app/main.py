"""
DRX Doctor Registration - FastAPI Backend

Feature-based structure:
  app/voice/              — voice extraction (STT + NER)
  app/onboarding_doctors/ — doctor registration (save to DB)
  app/specializations/    — specialization dropdown
  app/database.py         — MongoDB connection
"""

from contextlib import asynccontextmanager
from typing import Optional
from fastapi import FastAPI, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from app.config import validate_config
from app.utils.logger import setup_logging, get_dobo_logger, get_log_directory
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
    # Validate all required env vars
    validate_config()
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
    docs_url="/dobodb/docs",
    redoc_url="/dobodb/redoc",
    openapi_url="/dobodb/openapi.json"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch ALL unhandled exceptions and log them to dobo.log."""
    logger.error(
        f"Unhandled exception | method={request.method} path={request.url.path} "
        f"error={type(exc).__name__}: {str(exc)}",
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )

app.include_router(voice_router,           prefix="/dobodb/api/voice",           tags=["Voice"])
app.include_router(onboarding_router,      prefix="/dobodb/api/onboarding",      tags=["Onboarding Doctors"])
app.include_router(specializations_router, prefix="/dobodb/api/specializations", tags=["Specializations"])

# Root route
@app.get("/dobodb", include_in_schema=False)
async def root():
    return {"This is root of DOBO db."}


@app.get(
    "/dobodb/logs",
    tags=["Logs"],
    summary="View application logs (production log viewer)",
    description="""
Returns the contents of the `dobo.log` file as **plain text** so you can inspect what is
happening in production without shell access to the server.

### Query parameters
| Param | Default | Range | Purpose |
|-------|---------|-------|---------|
| `lines` | 100 | 1–5000 | Number of lines to return from the **end** of the log (most recent) |
| `level` | — | `ERROR` / `WARNING` / `INFO` / `DEBUG` | Return only lines at this level |

### Examples
- `/dobodb/logs` → last 100 log lines
- `/dobodb/logs?lines=500` → last 500 lines
- `/dobodb/logs?level=ERROR` → only error lines
- `/dobodb/logs?lines=200&level=WARNING` → last 200 warning lines

### Notes
- Every unhandled exception in the app is captured to this log via a global handler,
  so nothing silently disappears.
- Returns a friendly message (200) if the log file does not exist yet.
- Response content type is `text/plain`.
""",
    responses={
        200: {"description": "Log contents as plain text (or a message if no log exists yet)"},
        500: {"description": "Failed to read the log file"},
    },
)
async def get_logs(
    lines: int = Query(default=100, ge=1, le=5000, description="Number of lines from the end"),
    level: Optional[str] = Query(default=None, description="Filter by level: ERROR, WARNING, INFO, DEBUG"),
):
    """Read dobo.log and return last N lines."""
    log_file = get_log_directory() / "dobo.log"

    if not log_file.exists():
        return PlainTextResponse("Log file not found. No logs written yet.", status_code=200)

    try:
        with open(log_file, "r", encoding="utf-8") as f:
            all_lines = f.readlines()
    except Exception as e:
        return PlainTextResponse(f"Failed to read log file: {str(e)}", status_code=500)

    # Filter by level if specified
    if level:
        level_upper = level.upper()
        all_lines = [line for line in all_lines if f"[{level_upper}]" in line]

    # Return last N lines
    tail_lines = all_lines[-lines:]

    return PlainTextResponse("".join(tail_lines), status_code=200)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8003, reload=True)
