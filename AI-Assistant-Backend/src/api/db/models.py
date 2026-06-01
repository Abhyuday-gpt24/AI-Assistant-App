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