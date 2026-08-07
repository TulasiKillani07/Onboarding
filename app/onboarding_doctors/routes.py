"""
onboarding/routes.py
--------------------
Thin router â€” no business logic here.
"""

from fastapi import APIRouter
from app.onboarding_doctors.schemas import RegisterDoctorRequest, RegisterDoctorResponse
from app.onboarding_doctors.service import register_doctor

router = APIRouter()


@router.post(
    "/register",
    response_model=RegisterDoctorResponse,
    status_code=201,
    summary="Register a doctor",
    description="""
Save a doctor into the onboarding database after the registration form is submitted.

Works for both **VOICE** and **MANUAL** registration â€” set `source` accordingly.

**Duplicate check:** Returns 409 if the same phone or email already exists.

**Note:** `drx_doctor_gid` will be null until the doctor is synced to DRX (Phase 3).
""",
    responses={
        201: {"description": "Doctor registered successfully"},
        409: {"description": "Duplicate phone or email"},
        422: {"description": "Validation error"},
    },
)
async def register(request: RegisterDoctorRequest) -> RegisterDoctorResponse:
    return await register_doctor(request)

