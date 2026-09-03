"""
Specializations Router
Provides the canonical specialization list for the frontend dropdown.
Response is computed once and cached — zero cost on repeated calls.
"""

from fastapi import APIRouter
from app.voice.schemas import SpecializationListResponse
from app.voice.ner.specialization_service import (
    specialization_service,
    TOP_SPECIALIZATIONS,
    CANONICAL_SPECIALIZATIONS,
)

router = APIRouter()

# Build once at module load — this data never changes at runtime
_rest = sorted([s for s in CANONICAL_SPECIALIZATIONS if s not in TOP_SPECIALIZATIONS])
_CACHED_RESPONSE = SpecializationListResponse(
    top=TOP_SPECIALIZATIONS,
    all=CANONICAL_SPECIALIZATIONS,
    ordered=TOP_SPECIALIZATIONS + _rest,
    total=len(CANONICAL_SPECIALIZATIONS),
)


@router.get(
    "",
    response_model=SpecializationListResponse,
    summary="Get the specialization master list",
    description="""
Returns the complete canonical list of medical specializations for the registration
form dropdown. The response is computed once and cached — repeated calls are free.

### Response fields
| Field | Purpose |
|-------|---------|
| `top` | The most common specializations (show these first) |
| `all` | Complete canonical list |
| `ordered` | `top` first, then the rest alphabetically — **use this for the dropdown** |
| `total` | Count of all specializations |

### Frontend usage
```js
const { ordered } = await fetch('/dobodb/api/specializations').then(r => r.json())
// populate the <select> dropdown with `ordered`
```

**Tip:** Prefer `ordered` for the best UX — common picks surface at the top,
everything else stays easy to find alphabetically.
""",
    responses={
        200: {"description": "Specialization list returned successfully"},
    },
)
async def get_specializations():
    return _CACHED_RESPONSE
