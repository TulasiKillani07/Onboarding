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
    summary="Register a doctor (VOICE or MANUAL)",
    description="""
Save a doctor into the onboarding database after the registration form is submitted,
then immediately attempt to sync the record to DRX.

Works for both **VOICE** and **MANUAL** registration — set the `source` field accordingly.

### Request body
| Field | Required | Notes |
|-------|----------|-------|
| `doctor_name` | yes | Full name, title stripped (min 8 chars) |
| `username` | yes | Unique login username |
| `password` | yes | 8–64 chars, must include uppercase, lowercase, number, and symbol |
| `email` | yes | Must be unique |
| `phone` | yes | 10 digits, optional `+91` prefix (stored as `+91XXXXXXXXXX`) |
| `specialization` | yes | Medical specialization (per-doctor). Accepts a value from `GET /dobodb/api/specializations` **or** any manual/custom free-text value. |
| `source` | yes | `VOICE` or `MANUAL` |
| `locations` | yes | Array of practice locations — **exactly one must be `PRIMARY`** |
| `transcript`, `ner_output`, `pipeline_output`, `auto_fill`, `corrections` | no | Voice session audit data (send when `source=VOICE`) |

### Location object fields
Each item in the `locations` array has these fields:

| Field | Type | Required | Allowed / predefined values |
|-------|------|----------|-----------------------------|
| `location_priority` | enum | yes | `PRIMARY`, `SECONDARY`, `OTHER` |
| `facility_type` | enum | yes | `HOSPITAL`, `CLINIC`, `POLYCLINIC`, `MEDICAL_CENTER`, `INSTITUTION OR MEDICAL COLLEGE`, `OTHER` |
| `facility_type_other` | string | only if `facility_type = OTHER` | free text |
| `location_name` | string | yes | institution name (hospital / clinic / college / etc.) |
| `latitude` | string | no | GPS latitude, e.g. `"17.385044"` |
| `longitude` | string | no | GPS longitude, e.g. `"78.486671"` |
| `address` | string | no | full address line |
| `area` | string | no | locality / area within the city |
| `city` | string | yes | city |
| `district` | string | yes | district |
| `state` | string | yes | state / province |
| `country` | string | yes | country |
| `postcode` | string | yes | postal / ZIP code |
| `location_source` | enum | no | `CURRENT_LOCATION`, `MAP_SEARCH`, `MANUAL` |
| `status` | enum | no (server default) | `ACTIVE`, `INACTIVE` (defaults to `ACTIVE`) |

**Frontend note:** these are the exact field names and predefined enum values the API accepts —
build your dropdowns and payload against this table.

### Locations rules
- **Exactly one** location with `location_priority = PRIMARY` (required).
- **At most one** with `location_priority = SECONDARY`.
- Any number with `location_priority = OTHER`.
- `location_name` holds the institution name (hospital / clinic / college / etc.).
- `facility_type` and `location_priority` are independent (e.g. a SECONDARY location can be a CLINIC).
- When `facility_type = OTHER`, put the description in `facility_type_other`.

### Duplicate handling
Returns **409** if the `phone`, `email`, or `username` already exists.

### DRX sync behavior
Sync to DRX is attempted immediately after saving:
- On success → `sync_status = SYNCED`, plain password removed from the record.
- On failure (DRX down, auth error, etc.) → doctor is **still saved** with `sync_status = FAILED`
  and the reason in `sync_error`. Use the retry endpoints to re-sync later.

The response always includes the current `sync_status` and `sync_error`.
""",
    responses={
        201: {"description": "Doctor registered successfully (check sync_status for DRX result)"},
        409: {"description": "Duplicate phone, email, or username"},
        422: {"description": "Validation error (e.g. no PRIMARY location, weak password, bad phone)"},
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
    summary="Retry DRX sync for one doctor",
    description="""
Manually retry syncing a single **FAILED** doctor to DRX.

Use this when DRX was temporarily unavailable and you want to push one specific record
without waiting for the automatic backoff schedule.

### Path parameter
- `onboarding_id` — the MongoDB `_id` of the doctor record (24-character hex string).

### Behavior
- Idempotent — if the doctor already exists in DRX, it returns success.
- Updates `sync_status`, `sync_attempts`, and `last_sync_attempt` on the record.

### Response
```json
{
  "onboarding_id": "6a8d45895bb0516317859acb",
  "sync_status": "SYNCED",
  "sync_error": null
}
```
""",
    responses={
        200: {"description": "Sync retry attempted — see sync_status/sync_error in the response"},
        404: {"description": "No doctor found for the given onboarding_id"},
        422: {"description": "onboarding_id is not a valid 24-character hex ObjectId"},
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
    summary="Retry all failed DRX syncs (batch)",
    description="""
Retry syncing **all FAILED** doctors to DRX, respecting an exponential backoff schedule.

### Backoff schedule (per doctor)
`1 min → 5 min → 15 min → 1 hr`

- Max **5 attempts** total per doctor (1 initial + 4 retries).
- A doctor is only retried once its backoff window since `last_sync_attempt` has elapsed.
- Doctors that have hit the max attempt count are skipped.

### Response
```json
{
  "retried": 4,
  "succeeded": 3,
  "failed": 1
}
```
- `retried` — how many doctors were attempted in this run
- `succeeded` — how many synced successfully
- `failed` — how many failed again
""",
    responses={
        200: {"description": "Batch retry summary (retried / succeeded / failed counts)"},
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
    summary="List onboarded doctors (paginated + filterable)",
    description="""
Get a paginated list of doctors stored in the onboarding database, newest first.

### Query parameters
| Param | Default | Range | Purpose |
|-------|---------|-------|---------|
| `page` | 1 | ≥ 1 | Page number |
| `limit` | 20 | 1–100 | Items per page |
| `sync_status` | — | `PENDING` / `SYNCED` / `FAILED` | Filter by DRX sync state |
| `source` | — | `VOICE` / `MANUAL` | Filter by how the doctor was registered |

### Response shape
```json
{
  "total": 52,
  "page": 1,
  "limit": 20,
  "doctors": [ { ...doctor with locations[]... } ]
}
```
- `total` is the count of records matching the filter (not just this page).
- Each doctor includes its full `locations[]` array.

### Backward compatibility
Older records stored a single `location` object plus a top-level `hospital`.
Those are automatically converted on read into a single `PRIMARY` / `HOSPITAL`
location so the response shape is always consistent.
""",
    responses={
        200: {"description": "Paginated list of onboarded doctors"},
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
                # New shape: locations[]. Old shape: single location + hospital.
                locations_resp = []
                if doc.get("locations"):
                    locations_resp = [LocationResponse(**loc) for loc in doc["locations"]]
                elif doc.get("location") or doc.get("hospital"):
                    legacy_loc = doc.get("location") or {}
                    locations_resp = [LocationResponse(
                        location_priority="PRIMARY",
                        facility_type="HOSPITAL",
                        location_name=doc.get("hospital"),
                        **legacy_loc,
                    )]

                doctors.append(DoctorListItem(
                    onboarding_id=str(doc["_id"]),
                    doctor_name=doc.get("doctor_name", ""),
                    username=doc.get("username", ""),
                    email=doc.get("email"),
                    phone=doc.get("phone"),
                    specialization=doc.get("specialization"),
                    source=doc.get("source", "MANUAL"),
                    status=doc.get("status", "ACTIVE"),
                    sync_status=doc.get("sync_status", "PENDING"),
                    sync_error=doc.get("sync_error"),
                    locations=locations_resp,
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
