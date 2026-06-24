"""Pure path / ownership / key-building helpers (no S3 calls).

Everything here is string math over storage keys. The layout is now per-CHAT:

    {user_id}/{chat_id}/{filename}              source file (doc or image)
    {user_id}/{chat_id}/markdown/{file_id}.md   converted Markdown for a doc
    {user_id}/{chat_id}/extracted/{file_id}/…   images pulled from a complex doc

`file_id` is a stable hash of the source `storage_path`, so the Markdown /
extracted-image sidecars for a file can always be re-derived from the source key
alone (no extra plumbing through the upload flow). Keeping these helpers S3-free
makes them trivial to unit-test and lets the ingestion pipeline reuse them
without a boto3 client.
"""

import hashlib

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


def _user_prefix(user_id):
    """Where all of a user's files live: '{user_id}/'(no leading folder anymore)."""
    return str(user_id)


def chat_prefix(user_id, chat_id):
    """The S3 prefix owning one chat's files: '{user_id}/{chat_id}'."""
    return f"{user_id}/{chat_id}"


def chat_file_key(user_id, chat_id, filename):
    """Where an uploaded source file lands: '{user_id}/{chat_id}/{filename}'.

    The original filename is kept (matches the documented layout). Same-named
    files within a chat overwrite — acceptable for the current scope.
    """
    return f"{chat_prefix(user_id, chat_id)}/{filename}"


def categorize(content_type):
    """Classify a file as images vs docs (no longer an S3 folder — just the
    classification the frontend / ChatAttachment use to ingest-vs-inline)."""
    if content_type in IMAGE_TYPES:
        return CATEGORY_IMAGES
    if content_type in DOC_TYPES:
        return CATEGORY_DOCS
    raise AppException(status_code=415, detail=f"Unsupported type: {content_type}")


def build_public_url(key):
    return f"{settings.SUPABASE_S3_ENDPOINT}/{settings.SUPABASE_BUCKET}/{key}"


def _owns_path(storage_path, user_id):
    """A path belongs to a user only if their id is one of its directory
    segments. Keys are minted as '{user_id}/{chat_id}/{filename}', so the owner's
    id is always the first folder segment (never the filename). This blocks one
    user from referencing another user's storage_path."""
    parts = storage_path.strip("/").split("/")
    return str(user_id) in parts[:-1]


def _split_owner_chat(storage_path):
    """('{user_id}', '{chat_id}') from a source key '{user_id}/{chat_id}/…'."""
    parts = storage_path.strip("/").split("/")
    if len(parts) < 2:
        raise AppException(status_code=400, detail=f"Malformed storage_path: {storage_path}")
    return parts[0], parts[1]


def file_id_for(storage_path):
    """Stable file id derived from the source key — used both as the metadata
    `file_id` and to name the Markdown / extracted-image sidecars."""
    return hashlib.md5(storage_path.encode()).hexdigest()[:16]


def markdown_key(storage_path):
    """Where the converted Markdown for a given source doc lives, under the same
    chat prefix: '{user_id}/{chat_id}/markdown/{file_id}.md'."""
    user_id, chat_id = _split_owner_chat(storage_path)
    return f"{user_id}/{chat_id}/{CATEGORY_MARKDOWN}/{file_id_for(storage_path)}.md"


def extracted_image_key(storage_path, image_name):
    """Where an image pulled out of a complex doc is stored, under the same chat
    prefix: '{user_id}/{chat_id}/extracted/{file_id}/{image_name}'."""
    user_id, chat_id = _split_owner_chat(storage_path)
    return (
        f"{user_id}/{chat_id}/{CATEGORY_EXTRACTED}/"
        f"{file_id_for(storage_path)}/{image_name}"
    )
