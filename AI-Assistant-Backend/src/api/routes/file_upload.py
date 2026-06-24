from fastapi import APIRouter, Depends, Query, Body
from src.api.s3_bucket.s3_bucket import get_s3_client
from src.api.deps import get_current_user
from src.api.db.models import User
from src.api.services.s3_bucket_service import (
    generate_presigned_urls,
    verify_attachments,
    list_files_from_s3,
    delete_file_from_s3,
)

router = APIRouter()


@router.post("/upload/presigned", tags=["Files"])
async def get_presigned_urls(
    files_metadata: list[dict] = Body(
        ...,
        example=[{"name": "report.pdf", "content_type": "application/pdf"}],
    ),
    chat_id: str = Query(..., description="Client-generated chat id the files belong to"),
    user: User = Depends(get_current_user),
    s3=Depends(get_s3_client),
):
    """Frontend calls this when the user attaches files that don't have a URL yet.
    Keys are scoped to the caller AND the chat: '{user_id}/{chat_id}/{filename}'."""
    return generate_presigned_urls(files_metadata, user.id, chat_id, s3)


@router.post("/attachments/verify", tags=["Files"])
async def verify_files(
    attachments: list[dict] = Body(
        ...,
        example=[{"original_name": "report.pdf", "storage_path": "attachments/uuid.pdf"}],
    ),
    user: User = Depends(get_current_user),
    s3=Depends(get_s3_client),
):
    """Backend verifies all attachments exist in S3 (and belong to the caller)
    before passing to AI."""
    verified = verify_attachments(attachments, user.id, s3)
    return {"attachments": verified, "total": len(verified)}


@router.get("/files", tags=["Files"])
async def list_files(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    s3=Depends(get_s3_client),
):
    return list_files_from_s3(user.id, limit, offset, s3)


@router.delete("/files", tags=["Files"])
async def delete_file(
    file_path: str = Query(..., description="Full storage path"),
    user: User = Depends(get_current_user),
    s3=Depends(get_s3_client),
):
    return delete_file_from_s3(file_path, user.id, s3)