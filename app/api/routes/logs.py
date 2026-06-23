from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.schemas.logs import LogFileContentResponse, LogFileListResponse
from app.services.log_service import list_log_files, read_log_file

router = APIRouter(prefix="/api/logs", tags=["logs"])


@router.get("/files", response_model=LogFileListResponse)
def get_log_files(
    _current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, object]:
    settings = get_settings()
    return {"items": list_log_files(settings.log_dir)}


@router.get("/files/{file_name}", response_model=LogFileContentResponse)
def get_log_file(
    file_name: str,
    tail: int = Query(default=500, ge=1, le=5000),
    _current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, object]:
    settings = get_settings()
    try:
        return read_log_file(file_name, settings.log_dir, tail)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid log file name",
        ) from exc
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Log file not found",
        ) from exc
