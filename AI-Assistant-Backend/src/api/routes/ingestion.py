"""RAG ingestion endpoint — deliberately separate from the chat/storage routers.

The frontend calls this right after a document finishes uploading to S3. The
actual conversion + embedding (heavy / slow) runs in a background task so the
request returns immediately and the user can keep chatting; per-document status
is tracked in the `ingestion_jobs` table and polled via GET /status. This is
the seam where a dedicated serverless compute worker would plug in.
"""

from fastapi import APIRouter, Depends, BackgroundTasks, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.api.deps import get_current_user
from src.api.db.database import get_db
from src.api.db.models import User, IngestionJob, now_utc
from src.api.schemas.schemas import IngestRequest
from src.api.exceptions import ForbiddenError
from src.api.services.s3_bucket_service import _owns_path, IMAGE_TYPES
from src.api.services.ingestion_service import run_ingestion_jobs, get_job_statuses

router = APIRouter()


@router.post("/process", tags=["Ingestion"])
async def process_uploads(
    req: IngestRequest,
    background: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger conversion + embedding for freshly-uploaded documents."""
    queued = []
    for f in req.files:
        # Ownership gate: only the owner's own paths may be ingested.
        if not _owns_path(f.storage_path, user.id):
            raise ForbiddenError(detail=f"File not owned by user: {f.storage_path}")
        # Images are sent to the chat model inline (base64); nothing to ingest.
        if f.content_type in IMAGE_TYPES:
            continue
        queued.append(f.model_dump())

    # Record a pending job per document so the UI can poll status immediately.
    for f in queued:
        res = await db.exec(
            select(IngestionJob).where(
                IngestionJob.user_id == user.id,
                IngestionJob.storage_path == f["storage_path"],
            )
        )
        job = res.first()
        if job is None:
            db.add(IngestionJob(
                user_id=user.id,
                storage_path=f["storage_path"],
                original_name=f["original_name"],
                content_type=f["content_type"],
                status="pending",
            ))
        else:  # re-ingest of the same path → reset
            job.status = "pending"
            job.method = None
            job.chunks = 0
            job.error = None
            job.updated_at = now_utc()
    await db.commit()

    if queued:
        background.add_task(run_ingestion_jobs, queued, user.id)

    return {"status": "accepted", "queued": len(queued), "skipped": len(req.files) - len(queued)}


@router.get("/status", tags=["Ingestion"])
async def ingestion_status(
    storage_paths: list[str] = Query(default=[]),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Current ingestion status for the given storage paths (caller-scoped)."""
    statuses = await get_job_statuses(db, user.id, storage_paths)
    return {"statuses": statuses}
