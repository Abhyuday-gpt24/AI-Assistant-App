"""Storage policy constants: allowed MIME types, limits, and the per-user S3 layout.

These are pure configuration values with no S3 dependency, kept separate so both
the web layer (presign/verify) and the ingestion pipeline can import them cheaply.
"""

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

# Per-CHAT S3 layout — source files live flat under '{user_id}/{chat_id}/':
#   {user_id}/{chat_id}/{filename}              source file (doc or image)
#   {user_id}/{chat_id}/markdown/{file_id}.md   converted Markdown output of a doc
#   {user_id}/{chat_id}/extracted/{file_id}/…   images pulled out of complex docs
#
# CATEGORY_IMAGES / CATEGORY_DOCS are NO LONGER S3 folder segments (files keep
# their original name). They survive only as the `category` classification the
# frontend uses to decide ingest-vs-inline and the ChatAttachment.category column.
CATEGORY_IMAGES = "images"
CATEGORY_DOCS = "docs"
CATEGORY_MARKDOWN = "markdown"
CATEGORY_EXTRACTED = "extracted"
