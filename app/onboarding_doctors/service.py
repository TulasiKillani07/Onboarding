"""
onboarding_doctors/service.py
-----------------------------
Registration service — ONLY registration.

Flow:
  1. Validate duplicates
  2. Save onboarding.doctors
  3. Save onboarding.onboarding_sessions
  4. Delegate sync to DRXSyncService

This service does NOT know about DRX URLs, JWTs, HTTP, or sync logic.
It simply says: drx_sync_service.sync(onboarding_id)
"""

from fastapi import HTTPException, status
from app.database import get_database, COLLECTION_DOCTORS
from app.onboarding_doctors.models import new_doctor_document, Source
from app.onboarding_doctors.schemas import RegisterDoctorRequest, RegisterDoctorResponse, LocationResponse
from app.onboarding_sessions.service import create_session
from app.drx.sync_service import DRXSyncService


async def register_doctor(request: RegisterDoctorRequest) -> RegisterDoctorResponse:
    """
    Register a doctor. Both VOICE and MANUAL call this.

    Steps:
      1. Duplicate check (phone + email)
      2. Save to onboarding.doctors (sync_status = PENDING)
      3. Save session to onboarding.onboarding_sessions
      4. Sync to DRX (delegated — this service doesn't know how)
      5. Return response with final sync_status
    """
    db  = get_database()
    col = db[COLLECTION_DOCTORS]

    # 1. Duplicate checks
    if request.phone:
        if await col.find_one({"phone": request.phone}):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A doctor with phone '{request.phone}' is already registered.",
            )
    if request.email:
        if await col.find_one({"email": request.email}):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A doctor with email '{request.email}' is already registered.",
            )

    # 2. Save doctor
    location_dict = request.location.model_dump() if request.location else None
    doc = new_doctor_document(
        doctor_name=request.doctor_name,
        email=request.email,
        phone=request.phone,
        hospital=request.hospital,
        specialization=request.specialization,
        source=request.source,
        location=location_dict,
    )
    result = await col.insert_one(doc)
    onboarding_id = str(result.inserted_id)

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

    # 4. Sync to DRX (delegated)
    success, error = await DRXSyncService.sync(onboarding_id)

    # 5. Reload to get updated sync_status
    from bson import ObjectId
    doc = await col.find_one({"_id": ObjectId(onboarding_id)})

    # Build response
    loc = None
    if doc.get("location"):
        loc = LocationResponse(**doc["location"])

    return RegisterDoctorResponse(
        onboarding_id=onboarding_id,
        doctor_name=doc["doctor_name"],
        email=doc.get("email"),
        phone=doc.get("phone"),
        hospital=doc.get("hospital"),
        specialization=doc.get("specialization"),
        source=Source(doc["source"]),
        status=doc["status"],
        sync_status=doc["sync_status"],
        location=loc,
        created_at=doc["created_at"],
    )
