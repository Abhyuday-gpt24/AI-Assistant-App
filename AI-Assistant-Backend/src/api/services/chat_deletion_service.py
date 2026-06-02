"""Full teardown of a chat and everything it owns.

A chat's footprint is spread across four stores, so deleting one cleanly means
clearing all of them:

  1. S3        — source files + converted Markdown + extracted images. Identified
                 from the `chat_attachments` rows; for chats that pre-date that
                 tracking we fall back to the doc `storage_path`s embedded in the
                 chat's Pinecone namespace metadata.
  2. Pinecone  — the whole namespace (= chat_id).
  3. Postgres  — the LangGraph checkpointer thread (resumable graph memory).
  4. Postgres  — the app rows: messages, ingestion jobs, chat_attachments, chat.

S3 / Pinecone / checkpointer cleanup is best-effort (logged, never fatal) so a
transient storage error can't strand the DB rows; the DB rows are the source of
truth for what the user sees, and they're deleted last, in one transaction.

Ownership is enforced by the caller (the route) BEFORE this runs.
"""

import asyncio
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, delete as sql_delete

from src.api.db.models import Chat, Message, IngestionJob, ChatAttachment
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


async def delete_chat(chat_id: str, user_id: str, db: AsyncSession, s3) -> dict:
    """Delete a chat and all of its S3 / Pinecone / checkpointer / DB state.

    The caller must have already verified the chat exists and is owned by
    `user_id`.
    """
    # 1) Gather the chat's attachments (the per-chat record of its files).
    res = await db.execute(
        select(ChatAttachment).where(ChatAttachment.chat_id == chat_id)
    )
    attachments = [
        {"storage_path": a.storage_path, "content_type": a.content_type}
        for a in res.scalars().all()
    ]

    # Fallback for chats created before attachment tracking: recover their
    # document paths from the Pinecone namespace metadata (off the event loop —
    # Pinecone calls are blocking).
    known_paths = {a["storage_path"] for a in attachments}
    fallback_paths = await asyncio.to_thread(
        collect_namespace_storage_paths, chat_id
    )
    for path in fallback_paths:
        if path not in known_paths:
            # These are documents (only docs get embedded), so no content_type
            # in IMAGE_TYPES → S3 cleanup will also remove markdown + extracted.
            attachments.append({"storage_path": path, "content_type": "application/octet-stream"})

    doc_paths = [a["storage_path"] for a in attachments
                 if a["content_type"] not in IMAGE_TYPES]

    # 2) S3 — source files + markdown + extracted images (best-effort).
    try:
        result = await asyncio.to_thread(
            delete_chat_attachments_from_s3, attachments, user_id, s3
        )
        logger.info("Chat %s: deleted %s S3 objects", chat_id, result.get("deleted"))
    except Exception:
        logger.warning("Chat %s: S3 cleanup failed", chat_id, exc_info=True)

    # 3) Pinecone namespace (best-effort).
    await asyncio.to_thread(delete_namespace, chat_id)

    # 4) LangGraph checkpointer thread (best-effort).
    await delete_chat_thread(chat_id)

    # 5) DB rows — last, and transactional. Ingestion jobs are keyed by
    # (user_id, storage_path), so clear the ones for this chat's documents.
    await db.execute(sql_delete(Message).where(Message.chat_id == chat_id))
    if doc_paths:
        await db.execute(
            sql_delete(IngestionJob).where(
                IngestionJob.user_id == user_id,
                IngestionJob.storage_path.in_(doc_paths),
            )
        )
    await db.execute(
        sql_delete(ChatAttachment).where(ChatAttachment.chat_id == chat_id)
    )
    await db.execute(sql_delete(Chat).where(Chat.id == chat_id))
    await db.commit()

    return {"deleted": True, "chat_id": chat_id}
