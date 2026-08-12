"""
drx/auth_service.py
-------------------
Authenticates with DRX using client_id + client_secret.
Returns a Service JWT for use in integration API calls.

Uses shared httpx.AsyncClient for connection pooling.
"""

import os
import time
import httpx
from typing import Optional
from dotenv import load_dotenv
from app.http_client import HttpClient
from app.utils.logger import get_dobo_logger

load_dotenv()

logger = get_dobo_logger(__name__)


class DRXAuthService:
    """Manages Service JWT for DRX integration."""

    _instance = None
    _token: Optional[str] = None
    _token_expires_at: float = 0

    DRX_BASE_URL      = os.getenv("DRX_BASE_URL", "http://localhost:8003")
    DRX_CLIENT_ID     = os.getenv("DRX_CLIENT_ID", "")
    DRX_CLIENT_SECRET = os.getenv("DRX_CLIENT_SECRET", "")

    AUTH_ENDPOINT = "/drx/api/v1/integration/auth/service-token"

    @classmethod
    def get_instance(cls) -> "DRXAuthService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def get_token(self) -> str:
        """
        Get a valid Service JWT. Re-authenticates if expired.
        Raises Exception if authentication fails.
        """
        if self._token and time.time() < self._token_expires_at:
            logger.debug("Using cached DRX service token")
            return self._token

        logger.info("Requesting new DRX service token")
        url = f"{self.DRX_BASE_URL}{self.AUTH_ENDPOINT}"
        payload = {
            "client_id":     self.DRX_CLIENT_ID,
            "client_secret": self.DRX_CLIENT_SECRET,
        }

        try:
            response = await HttpClient.request_with_retry(
                "POST", url, json=payload, max_retries=2,
            )
        except httpx.ConnectError:
            logger.error("DRX auth failed: service unavailable")
            raise Exception("DRX service unavailable - cannot authenticate")
        except httpx.TimeoutException:
            logger.error("DRX auth failed: timeout")
            raise Exception("DRX authentication timeout")

        if response.status_code != 200:
            logger.error(f"DRX auth failed: {response.status_code}")
            raise Exception(f"DRX authentication failed: {response.status_code} - {response.text}")

        data = response.json()
        self._token = data["access_token"]
        self._token_expires_at = time.time() + data.get("expires_in", 600) - 60

        logger.info(f"DRX service token obtained | expires_in={data.get('expires_in', 600)}s")
        return self._token

    def clear_token(self):
        """Force re-authentication on next call."""
        self._token = None
        self._token_expires_at = 0
        logger.info("DRX service token cleared (will re-auth on next call)")
