"""
config.py
---------
Single source of truth for all environment variables.

All modules import from here - no scattered os.getenv() calls.
Validates required vars at import time so the app fails fast
if something is missing.
"""

import os
from dotenv import load_dotenv

load_dotenv()


# ---------------------------------------------------------------------------
# MongoDB
# ---------------------------------------------------------------------------
MONGODB_URL   = os.getenv("MONGODB_URL", "")
DATABASE_NAME = os.getenv("DATABASE_NAME", "onboarding")

# ---------------------------------------------------------------------------
# Sarvam AI (STT)
# ---------------------------------------------------------------------------
SARVAM_API_KEY = os.getenv("SARVAM_API_KEY", "")

# ---------------------------------------------------------------------------
# DRX Integration
# ---------------------------------------------------------------------------
DRX_BASE_URL               = os.getenv("DRX_BASE_URL", "https://doctors-dr-x.onrender.com").rstrip("/")
DRX_REGISTER_ENDPOINT      = os.getenv("DRX_REGISTER_ENDPOINT", "/drxdb/integration/doctors/register")

# ---------------------------------------------------------------------------
# Proxzar OAuth (identity provider for DRX communication)
# ---------------------------------------------------------------------------
PROXZAR_BASE_URL           = os.getenv("PROXZAR_BASE_URL", "https://oauth2.proxzar.ai").rstrip("/")
PROXZAR_TOKEN_ENDPOINT     = os.getenv("PROXZAR_TOKEN_ENDPOINT", "/api/v1/token")
PROXZAR_USERNAME  = os.getenv("PROXZAR_USERNAME", "")
PROXZAR_PASSWORD  = os.getenv("PROXZAR_PASSWORD", "")

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOG_DIR   = os.getenv("LOG_DIR", "")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# ---------------------------------------------------------------------------
# Email (Gmail SMTP)
# ---------------------------------------------------------------------------
EMAIL_SENDER   = os.getenv("EMAIL_SENDER", "")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
def validate_config():
    """Validate required environment variables. Call at app startup."""
    errors = []
    if not MONGODB_URL:
        errors.append("MONGODB_URL")
    if not SARVAM_API_KEY:
        errors.append("SARVAM_API_KEY")
    if errors:
        raise RuntimeError(
            f"Missing required environment variables: {', '.join(errors)}. "
            "Check your .env file."
        )
