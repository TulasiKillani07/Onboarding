"""
drx/doctor_service.py
---------------------
Calls DRX integration API to register a doctor.

Responsibilities:
  - Get Service JWT from DRXAuthService
  - POST doctor data to DRX
  - Return success/failure

The onboarding feature calls THIS — never talks HTTP directly.
"""

import os
import requests
from typing import Optional
from dotenv import load_dotenv
from app.drx.auth_service import DRXAuthService
from app.drx.schemas import DRXDoctorCreatePayload, DRXLocationPayload

load_dotenv()


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

        The onboarding service only needs to know success or failure.
        """
        # Get Service JWT
        auth = DRXAuthService.get_instance()
        try:
            token = auth.get_token()
        except Exception as e:
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

        # Call DRX
        url = f"{cls.DRX_BASE_URL}{cls.REGISTER_ENDPOINT}"
        headers = {"Authorization": f"Bearer {token}"}

        try:
            response = requests.post(
                url,
                json=payload.model_dump(exclude_none=True),
                headers=headers,
                timeout=15,
            )
        except requests.exceptions.ConnectionError:
            return False, "DRX service unavailable"
        except requests.exceptions.Timeout:
            return False, "DRX request timeout"

        if response.status_code in (200, 201):
            return True, None

        # Handle failure
        try:
            detail = response.json().get("detail", response.text)
        except Exception:
            detail = response.text

        # If 401, token may be expired — clear it for next attempt
        if response.status_code == 401:
            auth.clear_token()
            return False, f"DRX auth token expired or invalid: {detail}"

        return False, f"DRX returned {response.status_code}: {detail}"
