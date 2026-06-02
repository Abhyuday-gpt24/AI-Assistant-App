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

# Per-user S3 layout under '{folder}/{user_id}/':
#   images/    standalone images (→ base64 to LLM)
#   docs/      source documents (→ RAG ingestion)
#   markdown/  converted Markdown output of each doc
#   extracted/ images pulled out of complex docs during vision conversion
CATEGORY_IMAGES = "images"
CATEGORY_DOCS = "docs"
CATEGORY_MARKDOWN = "markdown"
CATEGORY_EXTRACTED = "extracted"
