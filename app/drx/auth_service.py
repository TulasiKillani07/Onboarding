"""
drx/auth_service.py
-------------------
Authenticates with DRX using client_id + client_secret.
Returns a Service JWT for use in integration API calls.

This is NOT admin auth. This is service-to-service auth.
"""

import os
import time
import requests
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class DRXAuthService:
    """Manages Service JWT for DRX integration."""

    _instance = None
    _token: Optional[str] = None
    _token_expires_at: float = 0

    DRX_BASE_URL  = os.getenv("DRX_BASE_URL", "http://localhost:8003")
    DRX_CLIENT_ID = os.getenv("DRX_CLIENT_ID", "")
    DRX_CLIENT_SECRET = os.getenv("DRX_CLIENT_SECRET", "")

    AUTH_ENDPOINT = "/drx/api/v1/integration/auth/service-token"

    @classmethod
    def get_instance(cls) -> "DRXAuthService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def get_token(self) -> str:
        """
        Get a valid Service JWT. Re-authenticates if expired.
        Raises Exception if authentication fails.
        """
        if self._token and time.time() < self._token_expires_at:
            return self._token

        # Authenticate
        url = f"{self.DRX_BASE_URL}{self.AUTH_ENDPOINT}"
        payload = {
            "client_id":     self.DRX_CLIENT_ID,
            "client_secret": self.DRX_CLIENT_SECRET,
        }

        try:
            response = requests.post(url, json=payload, timeout=10)
        except requests.exceptions.ConnectionError:
            raise Exception("DRX service unavailable — cannot authenticate")
        except requests.exceptions.Timeout:
            raise Exception("DRX authentication timeout")

        if response.status_code != 200:
            raise Exception(f"DRX authentication failed: {response.status_code} — {response.text}")

        data = response.json()
        self._token = data["access_token"]
        # Refresh 60 seconds before expiry
        self._token_expires_at = time.time() + data.get("expires_in", 600) - 60

        return self._token

    def clear_token(self):
        """Force re-authentication on next call."""
        self._token = None
        self._token_expires_at = 0
