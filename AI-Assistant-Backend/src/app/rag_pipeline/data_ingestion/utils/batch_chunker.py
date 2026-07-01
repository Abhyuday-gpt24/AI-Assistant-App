"""Offline NEXT.JS-DOCS ingest worker — convert → chunk, fanned out across processes.

This is the local/bulk pipeline for loading the **Next.js documentation** into
the shared corpus (NOT per-user/per-chat uploads — that's the live
`ingestion_service`). It reads each local file and, **in memory only (no S3)**:

    read bytes → convert_to_markdown → chunk_markdown

Docs are vectors-only, so there are no S3 writes and any vision-extracted image
placeholders are dropped (no bucket to host them). It runs inside a
`ProcessPoolExecutor` so a large local corpus converts in parallel (conversion —
PDF/office/vision — is the heavy, CPU-bound step). The actual text splitting is
delegated to `markdown_chunker.chunk_markdown`, the single source of truth shared
with the live path. Embedding is NOT done here — the parent collects the returned
chunk dicts and embeds them once per batch (tagged with `source="company"` + topic).
"""

import logging
import os
from concurrent.futures import ProcessPoolExecutor
from functools import partial
from pathlib import Path

from src.api.services.s3_bucket_service import DOC_TYPES
from src.app.rag_pipeline.data_ingestion.markdown_converter import convert_to_markdown
from src.app.rag_pipeline.data_ingestion.markdown_converter.vision_converter import describe_image
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

# Text-like sources get a light HTML/badge cleanup; converter output for
# PDF/office is left as-is, like the live path.
_TEXT_TYPES = {"text/plain", "text/markdown", "text/html", "text/csv"}


def content_type_for(path) -> str | None:
    """MIME type for a local file by extension, or None if unsupported."""
    return EXT_TO_CONTENT_TYPE.get(Path(path).suffix.lower())


def _source_name(path: str, rel_root: str | None) -> str:
    """How a docs file is identified in chunk metadata (`filename`). Prefer the
    path RELATIVE to the ingest root (so nested `index.mdx` files stay
    distinguishable and citations are meaningful), falling back to the basename."""
    if not rel_root:
        return Path(path).name
    try:
        return str(Path(path).resolve().relative_to(Path(rel_root).resolve())).replace("\\", "/")
    except Exception:
        return Path(path).name


def ingest_file(path: str, rel_root: str | None = None) -> list[dict]:
    """Convert one local docs file IN MEMORY and return its chunk dicts
    (the parent embeds them, tagged with the run's topic). No S3: docs are
    vectors-only, so vision-extracted image placeholders are dropped (no bucket to
    host them) and `storage_path` stays empty. Each chunk's `source` is the file's
    path relative to `rel_root` (the ingest dir), so docs stay identifiable.

    Returns [] for unsupported / standalone-image files, or on any failure (which
    is logged), so one bad file never aborts the batch.
    """
    try:
        content_type = content_type_for(path)
        if content_type is None or content_type not in DOC_TYPES:
            return []  # unsupported / standalone image → skipped

        src = Path(path)
        data = src.read_bytes()
        filename = src.name
        source_name = _source_name(path, rel_root)

        # 1) convert → Markdown (in memory).
        result = convert_to_markdown(data, filename, content_type)
        markdown = result["markdown"] or ""

        # 2) No S3 to host extracted figures → fold each one's OCR + short
        #    description INTO the text (best-effort) so a chart/diagram isn't lost.
        #    The page text is already transcribed by the vision converter; this
        #    only recovers the standalone figures it appends as image markers.
        for img in result["images"]:
            marker = f"![{img['name']}](__IMG__{img['name']}__)"
            desc = describe_image(img["data"], img.get("content_type", "image/png"))
            markdown = markdown.replace(marker, f"\n\n[Image: {desc}]\n\n" if desc else "")
            # Safety: strip any bare placeholder that didn't match the full marker.
            markdown = markdown.replace(f"__IMG__{img['name']}__", "")

        # 3) light cleanup for text/markdown-like sources (strip stray HTML/badges).
        if content_type in _TEXT_TYPES:
            markdown = clean_markdown(markdown)

        if not markdown.strip():
            return []

        # 4) chunk (storage_path empty — docs aren't stored in S3).
        return chunk_markdown(markdown, source=source_name, storage_path="")
    except Exception:
        logger.exception("Offline docs ingest failed for %s", path)
        return []


def ingest_files_in_multiprocess(
    file_paths: list[str],
    rel_root: str = None,
    max_workers: int = None,
) -> list[dict]:
    """Run `ingest_file` over many files across processes; flatten the chunks.
    `rel_root` (the ingest dir) makes each chunk's `source` a relative path."""
    if not file_paths:
        return []
    if max_workers is None:
        max_workers = min(os.cpu_count(), len(file_paths))

    worker = partial(ingest_file, rel_root=rel_root)
    all_chunks = []
    with ProcessPoolExecutor(max_workers) as executor:
        for file_chunks in executor.map(worker, file_paths):
            all_chunks.extend(file_chunks)

    return all_chunks
