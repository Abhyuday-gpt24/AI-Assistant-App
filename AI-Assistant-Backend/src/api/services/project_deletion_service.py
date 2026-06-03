"""Full teardown of a project and everything its chats share.

A project owns a SHARED footprint (unlike a standalone chat, whose footprint is
its own): one Pinecone namespace (= project_id) holding every doc uploaded in any
of its chats, the S3 files behind those docs, and N chats each with their own
checkpointer thread + messages. Deleting the project clears all of it:

  1. S3        — every source file + Markdown + extracted images across all the
                 project's chats (from their `chat_attachments` rows; fallback to
                 the doc `storage_path`s in the project namespace's metadata).
  2. Pinecone  — the whole project namespace (= project_id), once.
  3. Postgres  — each chat's LangGraph checkpointer thread.
  4. Postgres  — the app rows: messages, ingestion jobs, chat_attachments, the
                 chats, and the project — last, in one transaction.

Steps 1–3 are best-effort (logged, never fatal) so a transient storage error
can't strand the DB rows. Ownership is enforced by the caller BEFORE this runs.
"""

import asyncio
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, delete as sql_delete

from src.api.db.models import Project, Chat, Message, IngestionJob, ChatAttachment
from src.api.services.s3_bucket_service import (
    IMAGE_TYPES,
    delete_chat_attachments_from_s3,
)
from src.api.services.chat_service import delete_chat_thread
from src.app.rag_pipeline.vector_store import (
    delete_namespace,
    collect_namespace_storage_paths,
)

logger = logging.getLogger(__name__)


async def delete_project(project_id: str, user_id: str, db: AsyncSession,
                         s3) -> dict:
    """Delete a project and all of its chats' S3 / Pinecone / checkpointer / DB
    state. The caller must have already verified the project exists and is owned
    by `user_id`."""
    # 1) Gather the project's chats and the files attached across all of them.
    res = await db.execute(select(Chat).where(Chat.project_id == project_id))
    chats = list(res.scalars().all())
    chat_ids = [c.id for c in chats]

    attachments: list[dict] = []
    if chat_ids:
        res = await db.execute(
            select(ChatAttachment).where(ChatAttachment.chat_id.in_(chat_ids))
        )
        attachments = [
            {"storage_path": a.storage_path, "content_type": a.content_type}
            for a in res.scalars().all()
        ]

    # Fallback for chats created before attachment tracking: recover doc paths
    # from the project namespace's vector metadata (off the event loop).
    known_paths = {a["storage_path"] for a in attachments}
    fallback_paths = await asyncio.to_thread(
        collect_namespace_storage_paths, project_id
    )
    for path in fallback_paths:
        if path not in known_paths:
            attachments.append(
                {"storage_path": path, "content_type": "application/octet-stream"}
            )

    doc_paths = [a["storage_path"] for a in attachments
                 if a["content_type"] not in IMAGE_TYPES]

    # 2) S3 — source files + markdown + extracted images (best-effort).
    if attachments:
        try:
            result = await asyncio.to_thread(
                delete_chat_attachments_from_s3, attachments, user_id, s3
            )
            logger.info("Project %s: deleted %s S3 objects", project_id,
                        result.get("deleted"))
        except Exception:
            logger.warning("Project %s: S3 cleanup failed", project_id, exc_info=True)

    # 3) Pinecone — the shared project namespace (best-effort).
    await asyncio.to_thread(delete_namespace, project_id)

    # 4) LangGraph checkpointer threads — one per chat (best-effort).
    for chat_id in chat_ids:
        await delete_chat_thread(chat_id)

    # 5) DB rows — last, and transactional.
    if chat_ids:
        await db.execute(sql_delete(Message).where(Message.chat_id.in_(chat_ids)))
        await db.execute(
            sql_delete(ChatAttachment).where(ChatAttachment.chat_id.in_(chat_ids))
        )
    if doc_paths:
        await db.execute(
            sql_delete(IngestionJob).where(
                IngestionJob.user_id == user_id,
                IngestionJob.storage_path.in_(doc_paths),
            )
        )
    await db.execute(sql_delete(Chat).where(Chat.project_id == project_id))
    await db.execute(sql_delete(Project).where(Project.id == project_id))
    await db.commit()

    return {"deleted": True, "project_id": project_id, "chats_deleted": len(chat_ids)}
