"""User-facing S3 operations behind the storage routes: presign uploads, verify
attachments exist, list, and delete — each enforcing the per-user ownership gate.
"""

import uuid

from botocore.exceptions import ClientError
from config import settings
from src.api.exceptions import AppException, NotFoundError, ForbiddenError

from src.api.services.s3_bucket_service.constants import (
    ALLOWED_TYPES,
    MAX_FILES_PER_MESSAGE,
    PRESIGNED_EXPIRY,
)
from src.api.services.s3_bucket_service.paths import (
    _user_prefix,
    _owns_path,
    categorize,
)


def generate_presigned_urls(files_metadata, folder, user_id, s3):
    """Generate presigned URLs for files that need uploading."""
    if len(files_metadata) > MAX_FILES_PER_MESSAGE:
        raise AppException(status_code=400, detail=f"Max {MAX_FILES_PER_MESSAGE} files per message")

    for f in files_metadata:
        if f.get("content_type") not in ALLOWED_TYPES:
            raise AppException(status_code=415, detail=f"Unsupported type: {f.get('content_type')}")

    urls = []
    for f in files_metadata:
        ext = f["name"].rsplit(".", 1)[-1] if "." in f["name"] else ""
        unique_name = f"{uuid.uuid4()}.{ext}" if ext else str(uuid.uuid4())
        # Scope to the owner AND route by type:
        #   '{folder}/{user_id}/{images|docs}/{uuid.ext}'
        category = categorize(f["content_type"])
        storage_path = f"{_user_prefix(folder, user_id)}/{category}/{unique_name}"

        try:
            presigned_url = s3.generate_presigned_url(
                "put_object",
                Params={
                    "Bucket": settings.SUPABASE_BUCKET,
                    "Key": storage_path,
                    "ContentType": f["content_type"],
                },
                ExpiresIn=PRESIGNED_EXPIRY,
            )

            urls.append({
                "original_name": f["name"],
                "storage_path": storage_path,
                "upload_url": presigned_url,
                "content_type": f["content_type"],
                "category": category,
                "expires_in": PRESIGNED_EXPIRY,
            })
        except ClientError as e:
            raise AppException(status_code=502, detail=f"S3 error: {e.response['Error']['Message']}")

    return {"urls": urls, "total": len(urls)}


def verify_attachments(attachments, user_id, s3):
    """Verify that all attached files actually exist in S3 before processing."""
    verified = []

    for attachment in attachments:
        # Ownership gate: a user may only reference files under their own prefix.
        if not _owns_path(attachment["storage_path"], user_id):
            raise ForbiddenError(detail=f"Attachment not owned by user: {attachment['storage_path']}")
        try:
            response = s3.head_object(
                Bucket=settings.SUPABASE_BUCKET,
                Key=attachment["storage_path"],
            )

            verified.append({
                "original_name": attachment.get("original_name"),
                "storage_path": attachment["storage_path"],
                "content_type": response["ContentType"],
                "size_bytes": response["ContentLength"],
                "public_url": f"{settings.SUPABASE_S3_ENDPOINT}/{settings.SUPABASE_BUCKET}/{attachment['storage_path']}",
                "verified": True,
            })
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                raise NotFoundError(detail=f"Attachment not found: {attachment['storage_path']}")
            raise AppException(status_code=502, detail=f"S3 error: {e.response['Error']['Message']}")

    return verified


def list_files_from_s3(folder, user_id, limit, offset, s3):
    try:
        # Always scope the listing to this user's prefix so they only see
        # their own files, never the whole bucket.
        kwargs = {
            "Bucket": settings.SUPABASE_BUCKET,
            "MaxKeys": limit,
            "Prefix": f"{_user_prefix(folder, user_id)}/",
        }

        response = s3.list_objects_v2(**kwargs)
        all_objects = response.get("Contents", [])
        paginated = all_objects[offset: offset + limit]

        files = []
        for obj in paginated:
            key = obj["Key"]
            files.append({
                "name": key.split("/")[-1],
                "storage_path": key,
                "size": obj.get("Size"),
                "last_modified": obj["LastModified"].isoformat(),
                "public_url": f"{settings.SUPABASE_S3_ENDPOINT}/{settings.SUPABASE_BUCKET}/{key}",
            })

        return {"files": files, "total": len(files)}

    except ClientError as e:
        raise AppException(status_code=502, detail=f"S3 error: {e.response['Error']['Message']}")


def delete_file_from_s3(file_path, user_id, s3):
    # Ownership gate: a user may only delete files under their own prefix.
    if not _owns_path(file_path, user_id):
        raise ForbiddenError(detail=f"File not owned by user: {file_path}")
    try:
        s3.head_object(Bucket=settings.SUPABASE_BUCKET, Key=file_path)
    except ClientError as e:
        if e.response["Error"]["Code"] == "404":
            raise NotFoundError(detail=f"File not found: {file_path}")
        raise AppException(status_code=502, detail=f"S3 error: {e.response['Error']['Message']}")

    s3.delete_object(Bucket=settings.SUPABASE_BUCKET, Key=file_path)
    return {"message": "File deleted successfully", "file_path": file_path}
