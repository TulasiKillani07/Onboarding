"""
drx/sync_service.py
-------------------
Synchronization service - separate from registration.

Responsibilities:
  - Load onboarding doctor
  - Call DRX integration API
  - Update sync_status, sync_attempts, last_sync_attempt
  - Retry failed syncs with exponential backoff

Registration doesn't know HOW sync works.
It just calls: DRXSyncService.sync(onboarding_id)
"""

from datetime import datetime, timezone
from bson import ObjectId
from app.database import get_database, COLLECTION_DOCTORS
from app.drx.doctor_service import DRXDoctorService
from app.utils.logger import get_dobo_logger

logger = get_dobo_logger(__name__)

# Retry intervals in seconds: 1 min, 5 min, 15 min, 1 hr
RETRY_INTERVALS = [60, 300, 900, 3600]
MAX_ATTEMPTS = len(RETRY_INTERVALS) + 1  # initial + retries


class DRXSyncService:
    """Synchronizes an onboarding doctor to DRX."""

    @staticmethod
    async def sync(onboarding_id: str) -> tuple[bool, str | None]:
        """
        Sync a single doctor to DRX.
        """
        logger.info(f"Sync started | onboarding_id={onboarding_id}")

        db  = get_database()
        col = db[COLLECTION_DOCTORS]

        # 1. Load the doctor
        doc = await col.find_one({"_id": ObjectId(onboarding_id)})
        if not doc:
            logger.warning(f"Sync failed: doctor not found | onboarding_id={onboarding_id}")
            return False, f"Doctor not found: {onboarding_id}"

        # 2. Call DRX
        location = doc.get("location")
        success, error = await DRXDoctorService.register(
            doctor_name=doc["doctor_name"],
            email=doc.get("email"),
            phone=doc.get("phone"),
            hospital=doc.get("hospital"),
            specialization=doc.get("specialization"),
            source=doc.get("source", "VOICE"),
            location=location,
        )

        # 3. Update sync_status + tracking fields
        now = datetime.now(timezone.utc)
        current_attempts = doc.get("sync_attempts", 0) + 1

        if success:
            await col.update_one(
                {"_id": ObjectId(onboarding_id)},
                {"$set": {
                    "sync_status": "SYNCED",
                    "sync_error": None,
                    "sync_attempts": current_attempts,
                    "last_sync_attempt": now,
                    "updated_at": now,
                }},
            )
            logger.info(f"Sync success | onboarding_id={onboarding_id} attempt={current_attempts}")
        else:
            await col.update_one(
                {"_id": ObjectId(onboarding_id)},
                {"$set": {
                    "sync_status": "FAILED",
                    "sync_error": error,
                    "sync_attempts": current_attempts,
                    "last_sync_attempt": now,
                    "updated_at": now,
                }},
            )
            logger.warning(
                f"Sync failed | onboarding_id={onboarding_id} "
                f"attempt={current_attempts} error={error}"
            )

        return success, error

    @staticmethod
    async def retry_failed() -> dict:
        """
        Retry all FAILED syncs that are eligible for retry.
        """
        logger.info("Retry-all started")

        db  = get_database()
        col = db[COLLECTION_DOCTORS]
        now = datetime.now(timezone.utc)

        cursor = col.find({
            "sync_status": "FAILED",
            "sync_attempts": {"$lt": MAX_ATTEMPTS},
        })
        failed_docs = await cursor.to_list(length=100)

        retried = 0
        succeeded = 0
        failed = 0

        for doc in failed_docs:
            attempts = doc.get("sync_attempts", 0)
            last_attempt = doc.get("last_sync_attempt")

            # Check if enough time has passed (exponential backoff)
            if last_attempt and attempts > 0:
                interval_idx = min(attempts - 1, len(RETRY_INTERVALS) - 1)
                wait_seconds = RETRY_INTERVALS[interval_idx]
                elapsed = (now - last_attempt).total_seconds()
                if elapsed < wait_seconds:
                    continue  # Not yet time to retry

            onboarding_id = str(doc["_id"])
            success, _ = await DRXSyncService.sync(onboarding_id)
            retried += 1
            if success:
                succeeded += 1
            else:
                failed += 1

        logger.info(f"Retry-all complete | retried={retried} succeeded={succeeded} failed={failed}")
        return {"retried": retried, "succeeded": succeeded, "failed": failed}
