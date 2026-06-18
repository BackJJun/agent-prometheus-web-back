from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_current_user
from app.schemas.documents import (
    DocumentCreateRequest,
    DocumentListResponse,
    DocumentVersionListResponse,
    GeneralDocumentResponse,
    IndexJobListResponse,
)
from app.services.document_service import (
    create_document,
    get_document,
    list_document_versions,
    list_documents,
    list_index_jobs,
)

router = APIRouter(prefix="/api/documents", tags=["documents"])


def _user_id(current_user: dict[str, Any]) -> str:
    return str(current_user["id"])


@router.get("", response_model=DocumentListResponse)
async def get_documents(
    kind: Literal["general", "code"] = Query("general"),
    _current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, object]:
    return {"items": await list_documents(kind)}


@router.post("", response_model=GeneralDocumentResponse, status_code=status.HTTP_201_CREATED)
async def post_document(
    request: DocumentCreateRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, object]:
    return await create_document(_user_id(current_user), request.model_dump())


@router.get("/index-jobs", response_model=IndexJobListResponse)
async def get_index_jobs(
    kind: Literal["general", "code"] = Query("general"),
    _current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, object]:
    return {"items": await list_index_jobs(kind)}


@router.get("/{document_id}", response_model=GeneralDocumentResponse)
async def get_document_detail(
    document_id: UUID,
    _current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, object]:
    document = await get_document(document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return document


@router.get("/{document_id}/versions", response_model=DocumentVersionListResponse)
async def get_versions(
    document_id: UUID,
    _current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, object]:
    versions = await list_document_versions(document_id)
    if versions is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"items": versions}
