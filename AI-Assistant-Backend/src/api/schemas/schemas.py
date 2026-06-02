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
    attachments: List[Attachment] = []


# Ingestion schemas
class IngestFile(SQLModel):
    """One uploaded document to convert + embed into the user's RAG namespace."""
    storage_path: str
    original_name: str
    content_type: str

class IngestRequest(SQLModel):
    files: List[IngestFile]

class ChatSummary(SQLModel):
    id: str
    title: str
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