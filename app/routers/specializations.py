"""
Specializations router.
Provides the canonical specialization list for the frontend dropdown.
"""

from fastapi import APIRouter
from app.services.specialization_service import (
    specialization_service,
    TOP_SPECIALIZATIONS,
    CANONICAL_SPECIALIZATIONS,
)

router = APIRouter()


@router.get("", tags=["Specializations"])
async def get_specializations():
    """
    Returns all canonical specializations.
    Top 10 popular ones first, rest alphabetically sorted.
    """
    rest = sorted([s for s in CANONICAL_SPECIALIZATIONS if s not in TOP_SPECIALIZATIONS])
    return {
        "top": TOP_SPECIALIZATIONS,
        "all": CANONICAL_SPECIALIZATIONS,
        "ordered": TOP_SPECIALIZATIONS + rest,
        "total": len(CANONICAL_SPECIALIZATIONS),
    }
