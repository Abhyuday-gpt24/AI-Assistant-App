from sqlmodel import SQLModel
from pydantic import EmailStr


from pydantic import BaseModel
from typing import Optional, List



# Authentication schemas
class SignupRequest(SQLModel):
    email: EmailStr
    password: str
    name: str = ""

class LoginRequest(SQLModel):
    email: EmailStr
    password: str

class TokenResponse(SQLModel):
    access_token: str
    token_type: str = "bearer"


# Chat schemas
class Attachment(SQLModel):
    """A file the user attached, already uploaded to S3 via a presigned URL."""
    original_name: str
    storage_path: str

class ChatRequest(SQLModel):
    message: str
    chat_id: str | None = None
    # Set when the chat belongs to a project: on first send the chat row is
    # created under this project so its RAG namespace becomes the project's
    # shared corpus. Ignored for an already-persisted chat (the stored value wins).
    project_id: str | None = None
    attachments: List[Attachment] = []


# Ingestion schemas
class IngestFile(SQLModel):
    """One uploaded document to convert + embed into the chat's RAG namespace."""
    storage_path: str
    original_name: str
    content_type: str

class IngestRequest(SQLModel):
    # The docs get embedded into the chat's resolved RAG namespace. For a
    # standalone chat that's the chat_id; for a project chat it's the project_id
    # (shared corpus). The backend resolves it from the persisted chat when the
    # chat exists, else from project_id (below) when supplied. The frontend
    # generates chat_id for a new chat before the first message (upload time).
    chat_id: str
    project_id: str | None = None
    files: List[IngestFile]

class ChatSummary(SQLModel):
    id: str
    title: str
    updated_at: str


# Project schemas
class ProjectCreateRequest(SQLModel):
    name: str
    description: str = ""

class ProjectUpdateRequest(SQLModel):
    name: str | None = None
    description: str | None = None

class ProjectSummary(SQLModel):
    id: str
    name: str
    description: str
    created_at: str
    updated_at: str


# File upload schemas

class FileUploadResult(BaseModel):
    filename: str
    storage_path: str
    public_url: str
    size_bytes: int
    status: str

class FileUploadError(BaseModel):
    filename: str
    error: str
    status: str

class FileUploadResponse(BaseModel):
    uploaded: List[FileUploadResult]
    failed: List[FileUploadError]
    total: int
    successful: int

class FileInfo(BaseModel):
    name: Optional[str] = None
    storage_path: Optional[str] = None
    size: Optional[int] = None
    last_modified: Optional[str] = None   # S3 field
    public_url: Optional[str] = None

class FileListResponse(BaseModel):
    files: List[FileInfo]
    total: int

class FileDeleteResponse(BaseModel):
    message: str
    file_path: str