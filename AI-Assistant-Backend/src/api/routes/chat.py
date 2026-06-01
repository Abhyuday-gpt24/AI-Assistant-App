import json
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from src.api.db.database import get_db
from src.api.db.models import User, Chat, Message
from src.api.schemas.schemas import ChatRequest, ChatSummary
from src.api.deps import get_current_user
from sqlmodel import select
from src.api.services.chat_service import stream_chat

router = APIRouter()

@router.post("/chat/stream")
async def chat_stream(
    req: ChatRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Create new chat or use existing
    if req.chat_id:
        chat_id = req.chat_id
    else:
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
        async for chunk in stream_chat(req.message, chat_id):
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