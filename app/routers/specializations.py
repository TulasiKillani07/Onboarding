"""
Specializations Router
Provides the canonical specialization list for the frontend dropdown.
"""

from fastapi import APIRouter
from app.schemas.doctor import SpecializationListResponse
from app.onboarding_ner.specialization_service import (
    specialization_service,
    TOP_SPECIALIZATIONS,
    CANONICAL_SPECIALIZATIONS,
)

router = APIRouter()


@router.get(
    "",
    response_model=SpecializationListResponse,
    summary="Get all specializations",
    description="""
Returns the complete canonical specialization list for the registration form dropdown.

**Use `ordered`** — it puts the 10 most common specializations first, then the rest alphabetically.
This gives the best UX for the dropdown.

**Top 10 (shown first):**
General Physician, Cardiology, Dermatology, Pediatrics, Orthopedic Surgery,
Obstetrics & Gynecology, Neurology, Psychiatry, Ophthalmology, ENT

**Total:** 62 canonical specializations covering all major medical fields.

**Frontend usage:**
```js
const { ordered } = await fetch('/api/specializations').then(r => r.json())
// Use `ordered` to populate the <select> dropdown
```
""",
    responses={
        200: {"description": "Specialization list returned successfully"},
    },
)
async def get_specializations():
    rest = sorted([s for s in CANONICAL_SPECIALIZATIONS if s not in TOP_SPECIALIZATIONS])
    return SpecializationListResponse(
        top=TOP_SPECIALIZATIONS,
        all=CANONICAL_SPECIALIZATIONS,
        ordered=TOP_SPECIALIZATIONS + rest,
        total=len(CANONICAL_SPECIALIZATIONS),
    )
