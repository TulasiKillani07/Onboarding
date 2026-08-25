"""
onboarding_doctors/service.py
-----------------------------
Registration service - ONLY registration.

Flow:
  1. Validate duplicates
  2. Save onboarding.doctors
  3. Save onboarding.onboarding_sessions
  4. Delegate sync to DRXSyncService

This service does NOT know about DRX URLs, JWTs, HTTP, or sync logic.
It simply says: drx_sync_service.sync(onboarding_id)
"""

from fastapi import HTTPException, status
from pymongo.errors import DuplicateKeyError
from hashlib import sha256
from app.database import get_database, COLLECTION_DOCTORS
from app.onboarding_doctors.models import new_doctor_document, Source
from app.onboarding_doctors.schemas import RegisterDoctorRequest, RegisterDoctorResponse, LocationResponse
from app.onboarding_sessions.service import create_session
from app.drx.sync_service import DRXSyncService
from app.utils.logger import get_dobo_logger

logger = get_dobo_logger(__name__)


def _safe_str(value: str) -> str:
    """Ensure query value is a plain string, not a dict/operator."""
    if not isinstance(value, str):
        raise ValueError(f"Expected string, got {type(value).__name__}")
    return value


def _mask_phone(phone: str | None) -> str:
    """Mask phone for logging: 98****3210"""
    if not phone or len(phone) < 6:
        return "***"
    return f"{phone[:2]}****{phone[-4:]}"


def _mask_email(email: str | None) -> str:
    """Mask email for logging: r***@gmail.com"""
    if not email or "@" not in email:
        return "***"
    local, domain = email.split("@", 1)
    return f"{local[0]}***@{domain}"


async def register_doctor(request: RegisterDoctorRequest) -> RegisterDoctorResponse:
    """
    Register a doctor. Both VOICE and MANUAL call this.
    """
    logger.info(f"Registration started | source={request.source.value}")

    db  = get_database()
    col = db[COLLECTION_DOCTORS]

    # 1. Duplicate checks
    if request.phone:
        if await col.find_one({"phone": _safe_str(request.phone)}):
            logger.warning(f"Duplicate phone rejected | phone={_mask_phone(request.phone)}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A doctor with phone '{request.phone}' is already registered.",
            )
    if request.email:
        if await col.find_one({"email": _safe_str(request.email)}):
            logger.warning(f"Duplicate email rejected | email={_mask_email(request.email)}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A doctor with email '{request.email}' is already registered.",
            )
    if await col.find_one({"username": _safe_str(request.username)}):
        logger.warning("Duplicate username rejected")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Username '{request.username}' is already taken.",
        )

    # 2. Save doctor
    password_hash = sha256(request.password.encode()).hexdigest()
    location_dict = request.location.model_dump() if request.location else None
    doc = new_doctor_document(
        doctor_name=request.doctor_name,
        username=request.username,
        password_hash=password_hash,
        email=request.email,
        phone=request.phone,
        hospital=request.hospital,
        specialization=request.specialization,
        source=request.source,
        location=location_dict,
    )
    # Store plain password temporarily for DRX sync (removed after successful sync)
    doc["password"] = request.password
    try:
        result = await col.insert_one(doc)
    except DuplicateKeyError as e:
        logger.warning(f"DuplicateKeyError race condition | detail={str(e)[:100]}")
        detail = str(e)
        if "phone" in detail:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A doctor with phone '{request.phone}' is already registered.",
            )
        elif "email" in detail:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A doctor with email '{request.email}' is already registered.",
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Duplicate doctor detected.",
            )
    onboarding_id = str(result.inserted_id)
    logger.info(f"Doctor saved | onboarding_id={onboarding_id}")

    # 3. Save session
    final_submission = {
        "doctor_name":    request.doctor_name,
        "email":          request.email,
        "phone":          request.phone,
        "hospital":       request.hospital,
        "specialization": request.specialization,
        "source":         request.source.value,
    }
    if location_dict:
        final_submission["location"] = location_dict

    await create_session(
        onboarding_id=onboarding_id,
        source=request.source.value,
        final_submission=final_submission,
        transcript=request.transcript,
        ner_output=request.ner_output,
        pipeline_output=request.pipeline_output,
        auto_fill=request.auto_fill,
        corrections=request.corrections,
    )
    logger.info(f"Session saved | onboarding_id={onboarding_id}")

    # 4. Sync to DRX (delegated)
    success, error = await DRXSyncService.sync(onboarding_id)

    # 5. Reload to get updated sync_status
    from bson import ObjectId
    doc = await col.find_one({"_id": ObjectId(onboarding_id)})

    # Build response
    loc = None
    if doc.get("location"):
        loc = LocationResponse(**doc["location"])

    logger.info(
        f"Registration complete | onboarding_id={onboarding_id} "
        f"sync_status={doc['sync_status']}"
    )

    return RegisterDoctorResponse(
        onboarding_id=onboarding_id,
        doctor_name=doc["doctor_name"],
        username=doc["username"],
        email=doc.get("email"),
        phone=doc.get("phone"),
        hospital=doc.get("hospital"),
        specialization=doc.get("specialization"),
        source=Source(doc["source"]),
        status=doc["status"],
        sync_status=doc["sync_status"],
        sync_error=doc.get("sync_error"),
        location=loc,
        created_at=doc["created_at"],
    )
