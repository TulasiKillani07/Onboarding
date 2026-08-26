"""
onboarding/routes.py
--------------------
Thin router — no business logic here.
"""

from fastapi import APIRouter, HTTPException, Query, status
from datetime import datetime
from typing import Optional
from app.onboarding_doctors.schemas import RegisterDoctorRequest, RegisterDoctorResponse, DoctorListResponse, DoctorListItem, LocationResponse
from app.onboarding_doctors.service import register_doctor
from app.onboarding_doctors.models import Source, SyncStatus
from app.drx.sync_service import DRXSyncService
from app.database import get_database, COLLECTION_DOCTORS
from app.utils.logger import get_dobo_logger

logger = get_dobo_logger(__name__)

router = APIRouter()


@router.post(
    "/register",
    response_model=RegisterDoctorResponse,
    status_code=201,
    summary="Register a doctor",
    description="""
Save a doctor into the onboarding database after the registration form is submitted.

Works for both **VOICE** and **MANUAL** registration — set `source` accordingly.

**Duplicate check:** Returns 409 if the same phone or email already exists.

**DRX Sync:** Attempts to sync to DRX immediately. If DRX is unavailable,
doctor is still saved with sync_status=FAILED. Use retry endpoints to re-sync.
""",
    responses={
        201: {"description": "Doctor registered successfully"},
        409: {"description": "Duplicate phone or email"},
        422: {"description": "Validation error"},
    },
)
async def register(request: RegisterDoctorRequest) -> RegisterDoctorResponse:
    logger.info(f"POST /register | doctor_name={request.doctor_name} source={request.source.value}")
    try:
        result = await register_doctor(request)
        logger.info(f"POST /register success | onboarding_id={result.onboarding_id} sync_status={result.sync_status}")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"POST /register failed | error={str(e)}", exc_info=True)
        raise


@router.post(
    "/retry-sync/{onboarding_id}",
    summary="Retry DRX sync for a specific doctor",
    description="""
Manually retry syncing a FAILED doctor to DRX.

Use this when DRX was temporarily down and you want to push a specific doctor.
Idempotent — if doctor already exists in DRX, it returns success.
""",
    responses={
        200: {"description": "Sync retry result"},
        404: {"description": "Doctor not found"},
        422: {"description": "Invalid onboarding_id format"},
    },
)
async def retry_sync(onboarding_id: str):
    logger.info(f"POST /retry-sync | onboarding_id={onboarding_id}")
    # Validate ObjectId format (24 hex chars)
    if not onboarding_id or len(onboarding_id) != 24:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid onboarding_id format")
    try:
        int(onboarding_id, 16)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid onboarding_id format")

    success, error = await DRXSyncService.sync(onboarding_id)
    if error and "not found" in error.lower():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)

    logger.info(f"POST /retry-sync complete | onboarding_id={onboarding_id} success={success}")
    return {
        "onboarding_id": onboarding_id,
        "sync_status": "SYNCED" if success else "FAILED",
        "sync_error": error,
    }


@router.post(
    "/retry-sync-all",
    summary="Retry all failed DRX syncs",
    description="""
Retry syncing all FAILED doctors to DRX with exponential backoff.

Backoff schedule: 1 min -> 5 min -> 15 min -> 1 hr.
Max 5 attempts total (1 initial + 4 retries).

Only retries doctors whose backoff period has elapsed.
""",
    responses={
        200: {"description": "Retry summary"},
    },
)
async def retry_sync_all():
    logger.info("POST /retry-sync-all started")
    result = await DRXSyncService.retry_failed()
    logger.info(f"POST /retry-sync-all complete | {result}")
    return result


@router.get(
    "/doctors",
    response_model=DoctorListResponse,
    summary="List onboarded doctors",
    description="""
Get a paginated list of all doctors in the onboarding database.

**Filters:**
- `sync_status`: Filter by sync status (PENDING, SYNCED, FAILED)
- `source`: Filter by registration source (VOICE, MANUAL)

**Pagination:**
- `page`: Page number (default: 1)
- `limit`: Items per page (default: 20, max: 100)
""",
    responses={
        200: {"description": "List of onboarded doctors"},
    },
)
async def list_doctors(
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=20, ge=1, le=100, description="Items per page"),
    sync_status: Optional[str] = Query(default=None, description="Filter by sync status: PENDING, SYNCED, FAILED"),
    source: Optional[str] = Query(default=None, description="Filter by source: VOICE, MANUAL"),
):
    logger.info(f"GET /doctors | page={page} limit={limit} sync_status={sync_status} source={source}")
    try:
        db = get_database()
        col = db[COLLECTION_DOCTORS]

        # Build filter
        query = {}
        if sync_status:
            query["sync_status"] = sync_status.upper()
        if source:
            query["source"] = source.upper()

        # Get total count
        total = await col.count_documents(query)

        # Fetch paginated results (sorted by created_at descending)
        skip = (page - 1) * limit
        cursor = col.find(query).sort("created_at", -1).skip(skip).limit(limit)
        docs = await cursor.to_list(length=limit)

        # Build response
        doctors = []
        for doc in docs:
            try:
                loc = None
                if doc.get("location"):
                    loc = LocationResponse(**doc["location"])

                doctors.append(DoctorListItem(
                    onboarding_id=str(doc["_id"]),
                    doctor_name=doc.get("doctor_name", ""),
                    username=doc.get("username", ""),
                    email=doc.get("email"),
                    phone=doc.get("phone"),
                    hospital=doc.get("hospital"),
                    specialization=doc.get("specialization"),
                    source=doc.get("source", "MANUAL"),
                    status=doc.get("status", "ACTIVE"),
                    sync_status=doc.get("sync_status", "PENDING"),
                    sync_error=doc.get("sync_error"),
                    location=loc,
                    created_at=doc.get("created_at", doc.get("updated_at", datetime.now())),
                ))
            except Exception as e:
                logger.warning(f"Skipping malformed doc | _id={doc.get('_id')} error={str(e)}")
                continue

        logger.info(f"GET /doctors success | total={total} returned={len(doctors)}")
        return DoctorListResponse(
            total=total,
            page=page,
            limit=limit,
            doctors=doctors,
        )
    except Exception as e:
        logger.error(f"GET /doctors failed | error={str(e)}", exc_info=True)
        raise
