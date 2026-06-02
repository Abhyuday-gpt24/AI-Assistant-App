"""Per-user document ingestion: S3 source doc → Markdown → chunks → Pinecone.

This is the heavy-compute step (conversion + optional vision OCR + embeddings).
It's intentionally self-contained so it can run on a separate (serverless)
worker that the upload flow triggers; it only needs an S3 client and the
namespace-scoped vector store.

Pipeline per document:
  1. download source bytes from S3
  2. convert → Markdown (text / markitdown / pymupdf4llm / vision)
  3. upload any vision-extracted images to S3, swap placeholders → public URLs
  4. save the Markdown to S3 ('attachments/{user_id}/markdown/{uuid}.md')
  5. chunk the Markdown and embed into the user's Pinecone namespace (= user_id)
"""

import asyncio
import logging

from langchain_core.documents import Document
from sqlmodel import select

from src.api.db.database import SessionLocal
from src.api.db.models import IngestionJob, now_utc
from src.api.services.s3_bucket_service import (
    DOC_TYPES,
    download_bytes,
    upload_bytes,
    markdown_key,
    extracted_image_key,
)
from src.app.rag_pipeline.data_ingestion.markdown_converter import convert_to_markdown
from src.app.rag_pipeline.data_ingestion.utils.markdown_chunker import chunk_markdown
from src.app.rag_pipeline.vector_store import get_vector_store

logger = logging.getLogger(__name__)


def ingest_document(storage_path: str, original_name: str, content_type: str,
                    user_id: str, s3) -> dict:
    """Convert one uploaded document and embed it into the user's namespace."""
    if content_type not in DOC_TYPES:
        # Images aren't ingested — they're sent to the chat model inline.
        return {"storage_path": storage_path, "skipped": True, "reason": "not a document"}

    # 1) download
    data, _ = download_bytes(storage_path, s3)

    # 2) convert
    result = convert_to_markdown(data, original_name, content_type)
    markdown = result["markdown"] or ""

    # 3) upload extracted images + rewrite placeholders → public URLs
    for img in result["images"]:
        key = extracted_image_key(storage_path, user_id, img["name"])
        url = upload_bytes(key, img["data"], img["content_type"], s3)
        markdown = markdown.replace(f"__IMG__{img['name']}__", url)

    # 4) persist the Markdown alongside the source
    md_key = markdown_key(storage_path, user_id)
    upload_bytes(md_key, markdown.encode("utf-8"), "text/markdown", s3)

    # 5) chunk + embed into the per-user namespace
    chunks = chunk_markdown(markdown, source=original_name, storage_path=storage_path)
    if chunks:
        store = get_vector_store(namespace=user_id)
        documents = [
            Document(
                page_content=c["text"],
                metadata={
                    "source": c["source"],
                    "heading_trail": c["heading_trail"],
                    "storage_path": c["storage_path"],
                    "image_urls": c["image_urls"],
                    "user_id": user_id,
                },
            )
            for c in chunks
        ]
        store.add_documents(documents, ids=[c["chunk_id"] for c in chunks])

    return {
        "storage_path": storage_path,
        "markdown_path": md_key,
        "chunks": len(chunks),
        "method": result["method"],
        "profile": result.get("profile"),
        "skipped": False,
    }


async def _update_job(db, user_id: str, storage_path: str, **fields) -> None:
    """Patch an IngestionJob row's status (no-op if the row is missing)."""
    res = await db.exec(
        select(IngestionJob).where(
            IngestionJob.user_id == user_id,
            IngestionJob.storage_path == storage_path,
        )
    )
    job = res.first()
    if job is None:
        return
    for key, value in fields.items():
        setattr(job, key, value)
    job.updated_at = now_utc()
    await db.commit()


async def run_ingestion_jobs(files: list[dict], user_id: str) -> None:
    """Background entrypoint: ingest a batch, updating each job's DB status.

    Async so it can write status via the app's async DB session, but the heavy
    per-file conversion (sync, blocking) is pushed to a worker thread with
    `asyncio.to_thread` so it doesn't stall the event loop. Failures are
    isolated per file.
    """
    from src.api.s3_bucket.s3_bucket import get_s3_client

    s3 = get_s3_client()
    async with SessionLocal() as db:
        for f in files:
            await _update_job(db, user_id, f["storage_path"], status="processing")
            try:
                res = await asyncio.to_thread(
                    ingest_document,
                    f["storage_path"], f["original_name"], f["content_type"], user_id, s3,
                )
                await _update_job(
                    db, user_id, f["storage_path"],
                    status="ready", method=res.get("method"),
                    chunks=res.get("chunks", 0), error=None,
                )
                logger.info("Ingested %s → %s", f["storage_path"], res)
            except Exception as e:
                logger.exception("Ingestion failed for %s", f.get("storage_path"))
                await _update_job(
                    db, user_id, f["storage_path"], status="error", error=str(e)[:500],
                )


async def get_job_statuses(db, user_id: str, storage_paths: list[str]) -> list[dict]:
    """Current ingestion status for the given paths, scoped to the user."""
    if not storage_paths:
        return []
    res = await db.exec(
        select(IngestionJob).where(
            IngestionJob.user_id == user_id,
            IngestionJob.storage_path.in_(storage_paths),
        )
    )
    return [
        {
            "storage_path": j.storage_path,
            "status": j.status,
            "method": j.method,
            "chunks": j.chunks,
            "error": j.error,
        }
        for j in res.all()
    ]
