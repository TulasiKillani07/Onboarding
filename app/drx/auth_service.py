"""
drx/auth_service.py
-------------------
Authenticates with Proxzar OAuth to obtain a JWT for DRX communication.

DOBO has a dedicated Proxzar user (dobo_drx_integration).
This service obtains and caches the Proxzar JWT.
DRX trusts Proxzar and validates the token via JWKS.

DOBO does NOT verify or decode the JWT for authorization.
It only obtains the token and sends it to DRX.
"""

import time
import json
import base64
import httpx
from typing import Optional
from app.http_client import HttpClient
from app.config import PROXZAR_BASE_URL, PROXZAR_USERNAME, PROXZAR_PASSWORD
from app.utils.logger import get_dobo_logger

logger = get_dobo_logger(__name__)

# Safety buffer: refresh 60 seconds before actual expiry
TOKEN_REFRESH_BUFFER = 60


def _extract_exp_from_jwt(token: str) -> Optional[float]:
    """
    Extract the exp claim from a JWT without verifying it.
    DOBO is the consumer, not the validator.
    Returns unix timestamp or None if cannot be extracted.
    """
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        # Decode payload (second part)
        payload_b64 = parts[1]
        # Add padding if needed
        padding = 4 - len(payload_b64) % 4
        if padding != 4:
            payload_b64 += "=" * padding
        payload_json = base64.urlsafe_b64decode(payload_b64)
        payload = json.loads(payload_json)
        return payload.get("exp")
    except Exception:
        return None


class ProxzarAuthService:
    """Manages Proxzar JWT for DRX integration."""

    _instance = None
    _token: Optional[str] = None
    _token_expires_at: float = 0

    TOKEN_ENDPOINT = "/api/v1/token"

    @classmethod
    def get_instance(cls) -> "ProxzarAuthService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def get_token(self) -> str:
        """
        Get a valid Proxzar JWT. Re-authenticates if expired.
        Raises Exception if authentication fails.
        """
        if self._token and time.time() < self._token_expires_at:
            logger.debug("Using cached Proxzar token")
            return self._token

        logger.info("Requesting new Proxzar token")
        url = f"{PROXZAR_BASE_URL}{self.TOKEN_ENDPOINT}"

        # OAuth2 password grant — application/x-www-form-urlencoded
        # Include additional_claims for DRX to identify this as the DOBO integration identity
        form_data = {
            "grant_type": "password",
            "username": PROXZAR_USERNAME,
            "password": PROXZAR_PASSWORD,
            "additional_claims": '{"role":"integration","platform":"dobo"}',
        }

        try:
            response = await HttpClient.request_with_retry(
                "POST",
                url,
                data=form_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                max_retries=2,
            )
        except httpx.ConnectError:
            logger.error("Proxzar unavailable - cannot authenticate")
            raise Exception("Proxzar service unavailable - cannot authenticate")
        except httpx.TimeoutException:
            logger.error("Proxzar authentication timeout")
            raise Exception("Proxzar authentication timeout")

        if response.status_code != 200:
            logger.error(f"Proxzar auth failed: {response.status_code}")
            raise Exception(f"Proxzar authentication failed: {response.status_code} - {response.text}")

        data = response.json()
        access_token = data.get("accessToken") or data.get("access_token")

        if not access_token:
            logger.error("Proxzar response missing accessToken")
            raise Exception("Proxzar response missing accessToken")

        # Cache token using exp claim from JWT
        self._token = access_token
        exp = _extract_exp_from_jwt(access_token)
        if exp:
            self._token_expires_at = exp - TOKEN_REFRESH_BUFFER
            logger.info(f"Proxzar token obtained | expires_at={exp}")
        else:
            # Fallback: assume 15 min if exp cannot be extracted
            self._token_expires_at = time.time() + 900 - TOKEN_REFRESH_BUFFER
            logger.warning("Could not extract exp from Proxzar JWT, using 15 min default")

        return self._token

    def clear_token(self):
        """Force re-authentication on next call."""
        self._token = None
        self._token_expires_at = 0
        logger.info("Proxzar token cleared (will re-auth on next call)")
