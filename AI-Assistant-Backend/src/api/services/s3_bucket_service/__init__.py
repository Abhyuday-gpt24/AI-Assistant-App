"""S3 storage service.

Split by concern for readability; this package re-exports the same flat surface the
module used to expose, so `from src.api.services.s3_bucket_service import X` is
unchanged for every caller:

- constants  — allowed MIME types, limits, per-user S3 layout categories
- paths      — pure path / ownership / key-building helpers (no S3 calls)
- operations — presign / verify / list / delete (route-facing, ownership-gated)
- byte_io    — download / upload raw bytes for the ingestion pipeline
"""

from src.api.services.s3_bucket_service.constants import (
    IMAGE_TYPES,
    DOC_TYPES,
    ALLOWED_TYPES,
    MAX_FILES_PER_MESSAGE,
    PRESIGNED_EXPIRY,
    CATEGORY_IMAGES,
    CATEGORY_DOCS,
    CATEGORY_MARKDOWN,
    CATEGORY_EXTRACTED,
)
from src.api.services.s3_bucket_service.paths import (
    _user_prefix,
    categorize,
    build_public_url,
    _owns_path,
    chat_prefix,
    chat_file_key,
    file_id_for,
    markdown_key,
    extracted_image_key,
)
from src.api.services.s3_bucket_service.operations import (
    generate_presigned_urls,
    verify_attachments,
    list_files_from_s3,
    delete_file_from_s3,
    delete_chat_files_from_s3,
)
from src.api.services.s3_bucket_service.byte_io import (
    download_bytes,
    upload_bytes,
)

__all__ = [
    # constants
    "IMAGE_TYPES",
    "DOC_TYPES",
    "ALLOWED_TYPES",
    "MAX_FILES_PER_MESSAGE",
    "PRESIGNED_EXPIRY",
    "CATEGORY_IMAGES",
    "CATEGORY_DOCS",
    "CATEGORY_MARKDOWN",
    "CATEGORY_EXTRACTED",
    # paths
    "_user_prefix",
    "categorize",
    "build_public_url",
    "_owns_path",
    "chat_prefix",
    "chat_file_key",
    "file_id_for",
    "markdown_key",
    "extracted_image_key",
    # operations
    "generate_presigned_urls",
    "verify_attachments",
    "list_files_from_s3",
    "delete_file_from_s3",
    "delete_chat_files_from_s3",
    # byte_io
    "download_bytes",
    "upload_bytes",
]
