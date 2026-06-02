"""Offline batch ingest worker — convert → S3 → chunk, fanned out across processes.

The full per-file ingest mirrors the live `ingestion_service.ingest_document`,
but reads the source from local disk instead of S3:

    read bytes → convert_to_markdown → upload source + extracted images +
    converted Markdown to S3 → chunk_markdown (image URLs lifted into metadata)

It runs inside a `ProcessPoolExecutor` so a large local corpus converts in
parallel (conversion — PDF/office/vision — is the heavy, CPU-bound step). The
actual text splitting is delegated to `markdown_chunker.chunk_markdown`, the
single source of truth shared with the live path. Embedding is NOT done here —
the parent collects the returned chunk dicts and embeds them once per batch.
"""

import logging
import os
import uuid
from concurrent.futures import ProcessPoolExecutor
from functools import partial
from pathlib import Path

from src.api.services.s3_bucket_service import (
    DOC_TYPES,
    CATEGORY_DOCS,
    upload_bytes,
    markdown_key,
    extracted_image_key,
)
from src.app.rag_pipeline.data_ingestion.markdown_converter import convert_to_markdown
from src.app.rag_pipeline.data_ingestion.utils.markdown_chunker import chunk_markdown
from src.app.rag_pipeline.data_ingestion.utils.clean_markdown_file import clean_markdown

logger = logging.getLogger(__name__)

# Local file extension → MIME type. Only document types are ingested; standalone
# images are skipped (no extension entry here), exactly like the live path.
EXT_TO_CONTENT_TYPE = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".epub": "application/epub+zip",
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".mdx": "text/markdown",
    ".markdown": "text/markdown",
    ".html": "text/html",
    ".htm": "text/html",
    ".csv": "text/csv",
}

SUPPORTED_EXTENSIONS = frozenset(EXT_TO_CONTENT_TYPE)

# Text-like sources get a light HTML/badge cleanup (preserves the old offline
# behaviour); converter output for PDF/office is left as-is, like the live path.
_TEXT_TYPES = {"text/plain", "text/markdown", "text/html", "text/csv"}

# One boto3 client per worker process. boto3 clients are not fork/pickle-safe, so
# each process builds its own lazily on first use rather than receiving one.
_s3_client = None


def _s3():
    global _s3_client
    if _s3_client is None:
        from src.api.s3_bucket.s3_bucket import get_s3_client
        _s3_client = get_s3_client()
    return _s3_client


def content_type_for(path) -> str | None:
    """MIME type for a local file by extension, or None if unsupported."""
    return EXT_TO_CONTENT_TYPE.get(Path(path).suffix.lower())


def ingest_file(path: str, namespace: str, folder: str = "attachments") -> list[dict]:
    """Convert one local document and return its chunk dicts (parent embeds them).

    Mirrors the live `ingest_document`: the source doc, any vision-extracted
    images, and the converted Markdown are written to S3 under
    `{folder}/{namespace}/{docs,extracted,markdown}/…`, and each chunk carries the
    resulting public image URLs in its metadata. `namespace` doubles as the owner
    segment of the S3 keys and is the Pinecone namespace the chunks embed into.

    Returns [] for unsupported / standalone-image files, or on any failure (which
    is logged), so one bad file never aborts the batch.
    """
    try:
        content_type = content_type_for(path)
        if content_type is None or content_type not in DOC_TYPES:
            return []  # unsupported / standalone image → skipped, like the live path

        src = Path(path)
        data = src.read_bytes()
        filename = src.name
        s3 = _s3()

        # Synthesize the S3 key the file would have had if uploaded via the live
        # flow, so the existing key helpers + metadata semantics line up exactly.
        ext = src.suffix.lstrip(".")
        doc_id = uuid.uuid4().hex
        source_key = f"{folder}/{namespace}/{CATEGORY_DOCS}/{doc_id}.{ext}"

        # 0) put the source in S3 so chunk metadata's storage_path resolves.
        upload_bytes(source_key, data, content_type, s3)

        # 1) convert → Markdown.
        result = convert_to_markdown(data, filename, content_type)
        markdown = result["markdown"] or ""

        # 2) upload any vision-extracted images + rewrite placeholders → URLs.
        for img in result["images"]:
            key = extracted_image_key(source_key, namespace, img["name"], folder)
            url = upload_bytes(key, img["data"], img["content_type"], s3)
            markdown = markdown.replace(f"__IMG__{img['name']}__", url)

        # 3) light cleanup for text/markdown-like sources (strip stray HTML/badges).
        if content_type in _TEXT_TYPES:
            markdown = clean_markdown(markdown)

        if not markdown.strip():
            return []

        # 4) persist the Markdown alongside the source.
        upload_bytes(
            markdown_key(source_key, namespace, folder),
            markdown.encode("utf-8"),
            "text/markdown",
            s3,
        )

        # 5) chunk — chunk_markdown lifts image URLs into each chunk's metadata.
        return chunk_markdown(markdown, source=filename, storage_path=source_key)
    except Exception:
        logger.exception("Offline ingest failed for %s", path)
        return []


def ingest_files_in_multiprocess(
    file_paths: list[str],
    namespace: str,
    folder: str = "attachments",
    max_workers: int = None,
) -> list[dict]:
    """Run `ingest_file` over many files across processes; flatten the chunks."""
    if not file_paths:
        return []
    if max_workers is None:
        max_workers = min(os.cpu_count(), len(file_paths))

    worker = partial(ingest_file, namespace=namespace, folder=folder)
    all_chunks = []
    with ProcessPoolExecutor(max_workers) as executor:
        for file_chunks in executor.map(worker, file_paths):
            all_chunks.extend(file_chunks)

    return all_chunks
