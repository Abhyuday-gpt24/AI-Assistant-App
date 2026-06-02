import json
import asyncio
import logging
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from src.api.db.database import get_db
from src.api.db.models import User, Chat, Message
from src.api.schemas.schemas import ChatRequest, ChatSummary
from src.api.deps import get_current_user
from sqlmodel import select
import base64
from src.api.services.chat_service import stream_chat
from src.api.s3_bucket.s3_bucket import get_s3_client
from src.api.services.s3_bucket_service import (
    verify_attachments,
    download_bytes,
    markdown_key,
    IMAGE_TYPES,
)

router = APIRouter()
logger = logging.getLogger(__name__)


async def _attach_doc_markdown(att: dict, user_id: str, s3) -> None:
    """Make a just-attached document's text available to the model.

    Fast path: read the Markdown ingestion already saved to S3. Fallback (when
    ingestion hasn't finished yet): download the original and convert it on the
    fly, off the event loop. Either way sets att["doc_markdown"] (or None).
    """
    # Fast path — pre-converted Markdown from the ingestion pipeline.
    try:
        md_bytes, _ = download_bytes(markdown_key(att["storage_path"], user_id), s3)
        text = md_bytes.decode("utf-8", errors="replace").strip()
        if text:
            att["doc_markdown"] = text
            logger.info("doc content from S3 markdown for %s (%d chars)",
                        att["storage_path"], len(text))
            return
    except Exception:
        pass

    # Fallback — convert now so "attach + ask immediately" works regardless of
    # the async indexing race. Best-effort: if converter libs aren't present
    # (e.g. split serverless deploy), leave it None and the turn notes "indexing".
    try:
        data, _ = download_bytes(att["storage_path"], s3)

        def _convert():
            from src.app.rag_pipeline.data_ingestion.markdown_converter import (
                convert_to_markdown,
            )
            return convert_to_markdown(
                data, att.get("original_name") or "", att["content_type"]
            ).get("markdown")

        att["doc_markdown"] = (await asyncio.to_thread(_convert) or "").strip() or None
        logger.info("doc content via on-the-fly convert for %s (%s chars)",
                    att["storage_path"],
                    len(att["doc_markdown"]) if att.get("doc_markdown") else 0)
    except Exception:
        logger.warning("On-the-fly conversion failed for %s", att.get("storage_path"),
                       exc_info=True)
        att["doc_markdown"] = None

@router.post("/chat/stream")
async def chat_stream(
    req: ChatRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    s3=Depends(get_s3_client),
):
    # Confirm every attachment really exists in S3 before we start streaming.
    # Done up front (not inside generate()) so a missing file surfaces as a
    # normal HTTP error instead of a half-open event stream. Returns each file
    # enriched with content_type + public_url for the AI to consume.
    verified_attachments = []
    if req.attachments:
        verified_attachments = verify_attachments(
            [a.model_dump() for a in req.attachments], user.id, s3
        )
        for att in verified_attachments:
            if att.get("content_type") in IMAGE_TYPES:
                # Images go to the model INLINE as base64.
                data, _ = download_bytes(att["storage_path"], s3)
                b64 = base64.b64encode(data).decode("ascii")
                att["data_uri"] = f"data:{att['content_type']};base64,{b64}"
            else:
                # Documents: make the just-attached file's text available to the
                # model directly (fast path = pre-converted Markdown; fallback =
                # convert on the fly), independent of RAG retrieval.
                await _attach_doc_markdown(att, user.id, s3)

    # Resolve the chat. The frontend now generates the chat_id client-side (so it
    # can scope RAG ingestion to this chat's namespace before the first message),
    # so a supplied id may be either an existing chat OR a brand-new one.
    #
    # Security gate (mandatory): look the id up by itself.
    #   - exists & owned by caller  → resume it.
    #   - exists & owned by SOMEONE ELSE → 404. This is the attack case: a forged
    #     id would otherwise let a user inject messages into / resume another
    #     user's LangGraph thread (the checkpointer keys on thread_id == chat_id)
    #     or read their RAG namespace. 404 (not 403) so we don't leak which ids
    #     exist.
    #   - does not exist → create it with THIS id (client-supplied), owned by the
    #     caller. (Replaces the old server-generated implicit creation.)
    from fastapi import HTTPException
    if req.chat_id:
        result = await db.execute(select(Chat).where(Chat.id == req.chat_id))
        existing = result.scalar_one_or_none()
        if existing is not None:
            if existing.user_id != user.id:
                raise HTTPException(status_code=404, detail="Chat not found")
            chat_id = existing.id
        else:
            chat = Chat(id=req.chat_id, user_id=user.id, title=req.message[:50])
            db.add(chat)
            await db.commit()
            chat_id = chat.id
    else:
        # Legacy path: no client id supplied → server generates one.
        chat = Chat(user_id=user.id, title=req.message[:50])
        db.add(chat)
        await db.commit()
        chat_id = chat.id

    # Save user message
    db.add(Message(chat_id=chat_id, role="user", content=req.message))
    await db.commit()

    # Stream and collect full response
    async def generate():
        yield f"data: {json.dumps({'chat_id': chat_id})}\n\n"
        full_response = ""
        async for chunk in stream_chat(req.message, chat_id, verified_attachments, user.id):
            full_response += json.loads(chunk[6:]).get("delta", "") if "delta" in chunk else ""
            yield chunk

        # Save assistant message after stream completes
        db.add(Message(chat_id=chat_id, role="assistant", content=full_response))
        await db.commit()

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/chats")
async def list_chats(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Chat).where(Chat.user_id == user.id).order_by(Chat.updated_at.desc())
    )
    chats = result.scalars().all()
    return [ChatSummary(id=c.id, title=c.title, updated_at=str(c.updated_at)) for c in chats]


@router.get("/chats/{chat_id}/messages")
async def get_messages(
    chat_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Chat).where(Chat.id == chat_id, Chat.user_id == user.id)
    )
    if not result.scalar_one_or_none():
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Chat not found")

    result = await db.execute(
        select(Message).where(Message.chat_id == chat_id).order_by(Message.created_at)
    )
    messages = result.scalars().all()
    return [{"role": m.role, "content": m.content, "created_at": str(m.created_at)} for m in messages]