from typing import Annotated, Any

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.schemas.common import CurrentUserResponse

router = APIRouter(prefix="/api", tags=["me"])


@router.get("/me", response_model=CurrentUserResponse)
async def get_me(
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
) -> dict[str, Any]:
    return current_user
