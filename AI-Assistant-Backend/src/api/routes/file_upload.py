from fastapi import File, UploadFile, APIRouter, Depends, Query
from typing import Optional
from src.api.s3_bucket.s3_bucket import get_s3_client
from src.api.schemas.schemas import FileUploadResponse, FileListResponse, FileDeleteResponse
from src.api.services.s3_bucket_service import (
    upload_files_to_s3,
    list_files_from_s3,
    delete_file_from_s3,
)

router = APIRouter()


@router.post("/upload", response_model=FileUploadResponse, tags=["Files"])
async def upload_files(
    files: list[UploadFile] = File(...),
    folder: Optional[str] = Query(None),
    s3=Depends(get_s3_client),
):
    return await upload_files_to_s3(files, folder, s3)


@router.get("/files", response_model=FileListResponse, tags=["Files"])
async def list_files(
    folder: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    s3=Depends(get_s3_client),
):
    return list_files_from_s3(folder, limit, offset, s3)


@router.delete("/files", response_model=FileDeleteResponse, tags=["Files"])
async def delete_file(
    file_path: str = Query(..., description="Full storage path, e.g. data/images/uuid.jpg, data/doc/uuid.csv"),
    s3=Depends(get_s3_client),
):
    return delete_file_from_s3(file_path, s3)