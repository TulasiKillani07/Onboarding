"""
drx/doctor_service.py
---------------------
Calls DRX integration API to register a doctor.

Uses shared httpx.AsyncClient for connection pooling and retry.
"""

import httpx
from typing import Optional
from app.http_client import HttpClient
from app.drx.auth_service import ProxzarAuthService
from app.drx.schemas import DRXDoctorCreatePayload, DRXLocationPayload
from app.config import DRX_BASE_URL, DRX_REGISTER_ENDPOINT
from app.utils.logger import get_dobo_logger

logger = get_dobo_logger(__name__)


class DRXDoctorService:
    """Registers doctors in DRX via integration API."""

    @classmethod
    async def register(
        cls,
        doctor_name:    str,
        email:          str,
        phone:          Optional[str] = None,
        password:       Optional[str] = None,
        username:       Optional[str] = None,
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

        # Get Proxzar JWT
        auth = ProxzarAuthService.get_instance()
        try:
            token = await auth.get_token()
        except Exception as e:
            logger.error(f"Proxzar auth failed: {e}", exc_info=True)
            return False, f"Proxzar auth failed: {str(e)}"

        # Build payload
        loc_payload = None
        if location:
            loc_payload = DRXLocationPayload(**location)

        payload = DRXDoctorCreatePayload(
            name=doctor_name,
            username=username,
            email=email,
            phone=phone,
            password=password,
            hospital=hospital,
            specialization=specialization,
            source=source,
            location=loc_payload,
        )

        # Call DRX with retry
        url = f"{DRX_BASE_URL}{DRX_REGISTER_ENDPOINT}"
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
            logger.warning(f"DRX 401: Proxzar token rejected | detail={detail[:100]}")
            return False, f"DRX rejected Proxzar token: {detail}"

        logger.warning(f"DRX registration failed | status={response.status_code} detail={detail[:100]}")
        return False, f"DRX returned {response.status_code}: {detail}"
