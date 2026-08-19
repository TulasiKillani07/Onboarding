"""
database.py
-----------
Single database module for the onboarding service.

Responsibilities:
  - Read config from environment variables
  - Manage the single Motor client (connect / disconnect / ping)
  - Initialize collections and indexes on startup

No other file in this application creates a MongoClient directly.
"""

import os
import motor.motor_asyncio
from pymongo import ASCENDING, DESCENDING
from dotenv import load_dotenv
from app.utils.logger import get_dobo_logger

load_dotenv()

logger = get_dobo_logger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
MONGODB_URL   = os.getenv("MONGODB_URL", "")
DATABASE_NAME = os.getenv("DATABASE_NAME", "onboarding")

COLLECTION_DOCTORS             = "doctors"
COLLECTION_ONBOARDING_SESSIONS = "onboarding_sessions"


def _validate_config():
    if not MONGODB_URL:
        raise RuntimeError(
            "MONGODB_URL is not set. "
            "Add it to your .env file before starting the application."
        )


# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------
class DatabaseClient:
    """Single Motor client - reused across the entire application lifecycle."""

    _client: motor.motor_asyncio.AsyncIOMotorClient | None = None

    @classmethod
    def connect(cls):
        """Create the client. Called once at startup."""
        _validate_config()
        if cls._client is None:
            cls._client = motor.motor_asyncio.AsyncIOMotorClient(
                MONGODB_URL,
                serverSelectionTimeoutMS=5000,
            )
            logger.info(f"MongoDB client created -> database: {DATABASE_NAME}")

    @classmethod
    def disconnect(cls):
        """Close the client. Called at shutdown."""
        if cls._client is not None:
            cls._client.close()
            cls._client = None
            logger.info("MongoDB client closed")

    @classmethod
    def get_db(cls) -> motor.motor_asyncio.AsyncIOMotorDatabase:
        if cls._client is None:
            raise RuntimeError("Database not connected. Call DatabaseClient.connect() first.")
        return cls._client[DATABASE_NAME]

    @classmethod
    async def ping(cls) -> bool:
        """Return True if MongoDB is reachable."""
        try:
            await cls._client.admin.command("ping")
            return True
        except Exception:
            return False


def get_database() -> motor.motor_asyncio.AsyncIOMotorDatabase:
    """Convenience accessor - use this in feature services."""
    return DatabaseClient.get_db()


# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------
async def initialize_database():
    """
    Run at application startup.
    - Verify connection
    - Create collections if missing
    - Create required indexes
    No data is inserted.
    """
    reachable = await DatabaseClient.ping()
    if not reachable:
        raise RuntimeError(
            "Cannot connect to MongoDB. "
            "Check MONGODB_URL in .env and verify the cluster is accessible."
        )
    logger.info("MongoDB connection verified")

    db = DatabaseClient.get_db()
    existing_collections = await db.list_collection_names()

    # Collections
    for name in [COLLECTION_DOCTORS, COLLECTION_ONBOARDING_SESSIONS]:
        if name not in existing_collections:
            await db.create_collection(name)
            logger.info(f"Collection created: {name}")
        else:
            logger.debug(f"Collection exists: {name}")

    # Indexes
    # Drop legacy idx_doctor_gid if it exists (no longer used)
    doctors_col = db[COLLECTION_DOCTORS]
    existing_idx = await _existing_index_names(doctors_col)
    if "idx_doctor_gid" in existing_idx:
        await doctors_col.drop_index("idx_doctor_gid")
        logger.info("Dropped legacy index: doctors.idx_doctor_gid")

    await _create_doctors_indexes(db)
    await _create_sessions_indexes(db)

    logger.info("Database initialization complete")


async def _existing_index_names(collection) -> set:
    return set((await collection.index_information()).keys())


async def _create_doctors_indexes(db):
    col      = db[COLLECTION_DOCTORS]
    existing = await _existing_index_names(col)

    indexes = [
        {"key": [("phone",      ASCENDING)],  "unique": True,  "sparse": True,  "name": "idx_phone"},
        {"key": [("email",      ASCENDING)],  "unique": True,  "sparse": True,  "name": "idx_email"},
        {"key": [("username",   ASCENDING)],  "unique": True,  "sparse": True,  "name": "idx_username"},
    ]

    for idx in indexes:
        if idx["name"] not in existing:
            await col.create_index(idx["key"], unique=idx["unique"], sparse=idx["sparse"], name=idx["name"])
            logger.info(f"Index created: {COLLECTION_DOCTORS}.{idx['name']}")
        else:
            logger.debug(f"Index exists: {COLLECTION_DOCTORS}.{idx['name']}")


async def _create_sessions_indexes(db):
    col      = db[COLLECTION_ONBOARDING_SESSIONS]
    existing = await _existing_index_names(col)

    indexes = [
        {"key": [("session_id",  ASCENDING)],  "unique": True,  "name": "idx_session_id"},
        {"key": [("onboarding_id",  ASCENDING)],  "unique": False, "name": "idx_session_onboarding_id"},
        {"key": [("created_at",  DESCENDING)], "unique": False, "name": "idx_session_created_at"},
    ]

    for idx in indexes:
        if idx["name"] not in existing:
            await col.create_index(idx["key"], unique=idx["unique"], name=idx["name"])
            logger.info(f"Index created: {COLLECTION_ONBOARDING_SESSIONS}.{idx['name']}")
        else:
            logger.debug(f"Index exists: {COLLECTION_ONBOARDING_SESSIONS}.{idx['name']}")
