"""Pure path / ownership / key-building helpers (no S3 calls).

Everything here is string math over storage keys: where a user's files live, how a
key maps to a category, the ownership gate, and where converted Markdown / extracted
images for a doc are stored. Keeping these S3-free makes them trivial to unit-test
and lets the ingestion pipeline reuse them without a boto3 client.
"""

from config import settings
from src.api.exceptions import AppException

from src.api.services.s3_bucket_service.constants import (
    IMAGE_TYPES,
    DOC_TYPES,
    CATEGORY_IMAGES,
    CATEGORY_DOCS,
    CATEGORY_MARKDOWN,
    CATEGORY_EXTRACTED,
)


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
