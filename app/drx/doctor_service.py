"""
drx/doctor_service.py
---------------------
Calls DRX integration API to register a doctor.

Uses shared httpx.AsyncClient for connection pooling and retry.
"""

import os
import httpx
from typing import Optional
from dotenv import load_dotenv
from app.http_client import HttpClient
from app.drx.auth_service import DRXAuthService
from app.drx.schemas import DRXDoctorCreatePayload, DRXLocationPayload
from app.utils.logger import get_dobo_logger

load_dotenv()

logger = get_dobo_logger(__name__)


class DRXDoctorService:
    """Registers doctors in DRX via integration API."""

    DRX_BASE_URL = os.getenv("DRX_BASE_URL", "http://localhost:8003")
    REGISTER_ENDPOINT = "/drx/api/v1/integration/doctors/register"

    @classmethod
    async def register(
        cls,
        doctor_name:    str,
        email:          str,
        phone:          Optional[str] = None,
        hospital:       Optional[str] = None,
        specialization: Optional[str] = None,
        source:         str = "VOICE",
        location:       Optional[dict] = None,
    ) -> tuple[bool, Optional[str]]:
        """
        Register a doctor in DRX.

        Returns:
            (success: bool, error_message: str | None)
        """
        logger.info("DRX doctor registration started")

        # Get Service JWT
        auth = DRXAuthService.get_instance()
        try:
            token = await auth.get_token()
        except Exception as e:
            logger.error(f"DRX auth failed: {e}", exc_info=True)
            return False, f"DRX auth failed: {str(e)}"

        # Build payload
        loc_payload = None
        if location:
            loc_payload = DRXLocationPayload(**location)

        payload = DRXDoctorCreatePayload(
            name=doctor_name,
            email=email,
            phone=phone,
            hospital=hospital,
            specialization=specialization,
            source=source,
            location=loc_payload,
        )

        # Call DRX with retry
        url = f"{cls.DRX_BASE_URL}{cls.REGISTER_ENDPOINT}"
        headers = {"Authorization": f"Bearer {token}"}

        try:
            response = await HttpClient.request_with_retry(
                "POST",
                url,
                json=payload.model_dump(exclude_none=True),
                headers=headers,
                max_retries=2,
            )
        except httpx.ConnectError:
            logger.error("DRX unavailable: connection refused")
            return False, "DRX service unavailable"
        except httpx.TimeoutException:
            logger.error("DRX request timeout")
            return False, "DRX request timeout"

        if response.status_code in (200, 201):
            logger.info(f"DRX registration success | status={response.status_code}")
            return True, None

        # Handle failure
        try:
            detail = response.json().get("detail", response.text)
        except Exception:
            detail = response.text

        if response.status_code == 401:
            auth.clear_token()
            logger.warning(f"DRX 401: token expired | detail={detail[:100]}")
            return False, f"DRX auth token expired or invalid: {detail}"

        logger.warning(f"DRX registration failed | status={response.status_code} detail={detail[:100]}")
        return False, f"DRX returned {response.status_code}: {detail}"
