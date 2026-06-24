"""User-facing S3 operations behind the storage routes: presign uploads, verify
attachments exist, list, and delete — each enforcing the per-user ownership gate.
"""

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
    chat_prefix,
    chat_file_key,
    categorize,
)
from src.api.services.s3_bucket_service.byte_io import s3_error


def generate_presigned_urls(files_metadata, user_id, chat_id, s3):
    """Generate presigned PUT URLs for files, scoped to a single chat.

    Keys land at '{user_id}/{chat_id}/{filename}' (the original name is kept).
    `chat_id` is the client-generated id the frontend mints before the first
    message, so uploads can be scoped to the chat up front.
    """
    if not chat_id:
        raise AppException(status_code=400, detail="chat_id is required for upload")
    if len(files_metadata) > MAX_FILES_PER_MESSAGE:
        raise AppException(status_code=400, detail=f"Max {MAX_FILES_PER_MESSAGE} files per message")

    for f in files_metadata:
        if f.get("content_type") not in ALLOWED_TYPES:
            raise AppException(status_code=415, detail=f"Unsupported type: {f.get('content_type')}")

    urls = []
    for f in files_metadata:
        # Per-chat key, original filename preserved: '{user_id}/{chat_id}/{name}'.
        # `category` is no longer a folder — it's just the images/docs hint the
        # frontend uses to ingest-vs-inline.
        category = categorize(f["content_type"])
        storage_path = chat_file_key(user_id, chat_id, f["name"])

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
            raise s3_error(e)

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
            raise s3_error(e)

    return verified


def list_files_from_s3(user_id, limit, offset, s3):
    try:
        # Always scope the listing to this user's prefix so they only see
        # their own files, never the whole bucket.
        kwargs = {
            "Bucket": settings.SUPABASE_BUCKET,
            "MaxKeys": limit,
            "Prefix": f"{_user_prefix(user_id)}/",
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
        raise s3_error(e)


def delete_file_from_s3(file_path, user_id, s3):
    # Ownership gate: a user may only delete files under their own prefix.
    if not _owns_path(file_path, user_id):
        raise ForbiddenError(detail=f"File not owned by user: {file_path}")
    try:
        s3.head_object(Bucket=settings.SUPABASE_BUCKET, Key=file_path)
    except ClientError as e:
        if e.response["Error"]["Code"] == "404":
            raise NotFoundError(detail=f"File not found: {file_path}")
        raise s3_error(e)

    s3.delete_object(Bucket=settings.SUPABASE_BUCKET, Key=file_path)
    return {"message": "File deleted successfully", "file_path": file_path}


def _list_prefix_keys(prefix, s3):
    """Every object key under a prefix (paginated). Empty list if none."""
    keys = []
    token = None
    while True:
        kwargs = {"Bucket": settings.SUPABASE_BUCKET, "Prefix": prefix}
        if token:
            kwargs["ContinuationToken"] = token
        resp = s3.list_objects_v2(**kwargs)
        keys.extend(o["Key"] for o in resp.get("Contents", []))
        if resp.get("IsTruncated"):
            token = resp.get("NextContinuationToken")
        else:
            break
    return keys


def _delete_keys(keys, s3):
    """Batch-delete keys (S3 caps delete_objects at 1000 per call)."""
    keys = list(dict.fromkeys(k for k in keys if k))  # de-dup, drop falsy
    for i in range(0, len(keys), 1000):
        batch = keys[i:i + 1000]
        s3.delete_objects(
            Bucket=settings.SUPABASE_BUCKET,
            Delete={"Objects": [{"Key": k} for k in batch], "Quiet": True},
        )
    return len(keys)


def delete_chat_files_from_s3(user_id, chat_id, s3):
    """Delete EVERY S3 object under a chat's prefix '{user_id}/{chat_id}/' — the
    source files, converted Markdown, and extracted images all live there now, so
    one prefix sweep cleans the chat completely. Ownership-gated by construction
    (the prefix is the caller's own). Idempotent: an empty prefix deletes nothing.
    """
    prefix = f"{chat_prefix(user_id, chat_id)}/"
    keys = _list_prefix_keys(prefix, s3)
    deleted = _delete_keys(keys, s3)
    return {"deleted": deleted}
