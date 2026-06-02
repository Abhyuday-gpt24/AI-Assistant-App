from botocore.exceptions import ClientError
from config import settings
from src.api.exceptions import AppException, NotFoundError, ForbiddenError
import uuid


# Standalone images: NOT ingested into RAG — they are streamed to the chat model
# inline as base64 at query time. Documents: converted to Markdown and embedded.
IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
DOC_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # .docx
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",  # .pptx
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # .xlsx
    "application/epub+zip",  # .epub
    "text/plain",
    "text/html",
    "text/csv",
    "text/markdown",
}
ALLOWED_TYPES = IMAGE_TYPES | DOC_TYPES
MAX_FILES_PER_MESSAGE = 10
PRESIGNED_EXPIRY = 600  # 10 minutes

# Per-user S3 layout under '{folder}/{user_id}/':
#   images/    standalone images (→ base64 to LLM)
#   docs/      source documents (→ RAG ingestion)
#   markdown/  converted Markdown output of each doc
#   extracted/ images pulled out of complex docs during vision conversion
CATEGORY_IMAGES = "images"
CATEGORY_DOCS = "docs"
CATEGORY_MARKDOWN = "markdown"
CATEGORY_EXTRACTED = "extracted"


def _user_prefix(folder, user_id):
    """Where a given user's files live: '{folder}/{user_id}' (or just the id)."""
    return f"{folder}/{user_id}" if folder else str(user_id)


def categorize(content_type):
    """Which subfolder a file belongs in, based on its MIME type."""
    if content_type in IMAGE_TYPES:
        return CATEGORY_IMAGES
    if content_type in DOC_TYPES:
        return CATEGORY_DOCS
    raise AppException(status_code=415, detail=f"Unsupported type: {content_type}")


def build_public_url(key):
    return f"{settings.SUPABASE_S3_ENDPOINT}/{settings.SUPABASE_BUCKET}/{key}"


def _owns_path(storage_path, user_id):
    """A path belongs to a user only if their id is one of its directory
    segments. Keys are minted as '{folder}/{user_id}/{uuid.ext}', so the owner's
    id always appears as a folder segment (never the filename). This blocks one
    user from referencing another user's storage_path."""
    parts = storage_path.strip("/").split("/")
    return str(user_id) in parts[:-1]


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


# ─────────────────────────────────────────────────────────────────────────────
# Byte-level helpers used by the ingestion pipeline (download source docs, write
# converted Markdown + extracted images back to S3).
# ─────────────────────────────────────────────────────────────────────────────

def download_bytes(storage_path, s3):
    """Fetch an object's raw bytes (+ its content type)."""
    try:
        resp = s3.get_object(Bucket=settings.SUPABASE_BUCKET, Key=storage_path)
        return resp["Body"].read(), resp.get("ContentType")
    except ClientError as e:
        if e.response["Error"]["Code"] in ("404", "NoSuchKey"):
            raise NotFoundError(detail=f"File not found: {storage_path}")
        raise AppException(status_code=502, detail=f"S3 error: {e.response['Error']['Message']}")


def upload_bytes(key, data, content_type, s3):
    """Write raw bytes to S3 and return the object's public URL."""
    try:
        s3.put_object(
            Bucket=settings.SUPABASE_BUCKET,
            Key=key,
            Body=data,
            ContentType=content_type,
        )
        return build_public_url(key)
    except ClientError as e:
        raise AppException(status_code=502, detail=f"S3 error: {e.response['Error']['Message']}")


def _doc_uuid(storage_path):
    """The uuid stem of a doc key, e.g. '.../docs/abc123.pdf' → 'abc123'."""
    return storage_path.rsplit("/", 1)[-1].rsplit(".", 1)[0]


def markdown_key(storage_path, user_id, folder="attachments"):
    """Where the converted Markdown for a given source doc lives."""
    return f"{_user_prefix(folder, user_id)}/{CATEGORY_MARKDOWN}/{_doc_uuid(storage_path)}.md"


def extracted_image_key(storage_path, user_id, image_name, folder="attachments"):
    """Where an image pulled out of a complex doc is stored."""
    return (
        f"{_user_prefix(folder, user_id)}/{CATEGORY_EXTRACTED}/"
        f"{_doc_uuid(storage_path)}/{image_name}"
    )