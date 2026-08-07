"""
drx/sync_service.py
-------------------
Synchronization service — separate from registration.

Responsibilities:
  - Load onboarding doctor
  - Call DRX integration API
  - Update sync_status (SYNCED / FAILED + sync_error)

Registration doesn't know HOW sync works.
It just calls: DRXSyncService.sync(onboarding_id)
"""

from bson import ObjectId
from app.database import get_database, COLLECTION_DOCTORS
from app.drx.doctor_service import DRXDoctorService


class DRXSyncService:
    """Synchronizes an onboarding doctor to DRX."""

    @staticmethod
    async def sync(onboarding_id: str) -> tuple[bool, str | None]:
        """
        Sync a single doctor to DRX.

        Steps:
          1. Load doctor from onboarding.doctors
          2. Call DRX integration API
          3. Update sync_status

        Returns:
          (success: bool, error: str | None)
        """
        db  = get_database()
        col = db[COLLECTION_DOCTORS]

        # 1. Load the doctor
        doc = await col.find_one({"_id": ObjectId(onboarding_id)})
        if not doc:
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

        # 3. Update sync_status
        if success:
            await col.update_one(
                {"_id": ObjectId(onboarding_id)},
                {"$set": {"sync_status": "SYNCED", "sync_error": None}},
            )
        else:
            await col.update_one(
                {"_id": ObjectId(onboarding_id)},
                {"$set": {"sync_status": "FAILED", "sync_error": error}},
            )

        return success, error
