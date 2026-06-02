from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime
import uuid


def now_utc():
    return datetime.now(timezone.utc)


def new_id():
    return str(uuid.uuid4())


def utc_datetime_column():
    return Column(DateTime(timezone=True))


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: str = Field(default_factory=new_id, primary_key=True)
    email: str = Field(unique=True, index=True)
    hashed_password: str
    name: str = ""
    created_at: datetime = Field(
        default_factory=now_utc,
        sa_column=Column(DateTime(timezone=True))
    )

    chats: list["Chat"] = Relationship(back_populates="user")


class Chat(SQLModel, table=True):
    __tablename__ = "chats"

    id: str = Field(default_factory=new_id, primary_key=True)
    user_id: str = Field(foreign_key="users.id")
    title: str = "New Chat"
    created_at: datetime = Field(
        default_factory=now_utc,
        sa_column=Column(DateTime(timezone=True))
    )
    updated_at: datetime = Field(
        default_factory=now_utc,
        sa_column=Column(DateTime(timezone=True))
    )

    user: User | None = Relationship(back_populates="chats")
    messages: list["Message"] = Relationship(back_populates="chat")


class Message(SQLModel, table=True):
    __tablename__ = "messages"

    id: str = Field(default_factory=new_id, primary_key=True)
    chat_id: str = Field(foreign_key="chats.id")
    role: str  # "user" or "assistant"
    content: str
    created_at: datetime = Field(
        default_factory=now_utc,
        sa_column=Column(DateTime(timezone=True))
    )

    chat: Chat | None = Relationship(back_populates="messages")


class IngestionJob(SQLModel, table=True):
    """Tracks RAG ingestion of one uploaded document so the UI can show
    indexing → ready/error. Keyed by (user_id, storage_path); persisted in
    Postgres so a separate serverless ingestion worker can update it too."""
    __tablename__ = "ingestion_jobs"

    id: str = Field(default_factory=new_id, primary_key=True)
    user_id: str = Field(foreign_key="users.id", index=True)
    storage_path: str = Field(index=True)
    original_name: str
    content_type: str
    status: str = "pending"  # pending | processing | ready | error
    method: str | None = None  # which converter ran (pymupdf4llm / vision / ...)
    chunks: int = 0
    error: str | None = None
    created_at: datetime = Field(
        default_factory=now_utc,
        sa_column=Column(DateTime(timezone=True))
    )
    updated_at: datetime = Field(
        default_factory=now_utc,
        sa_column=Column(DateTime(timezone=True))
    )