"""Project routes — workspaces that group chats over a SHARED RAG corpus.

A project is created first (name + description); its generated id is the Pinecone
namespace every doc uploaded in any of its chats is embedded into, so all chats
in the project retrieve over the same knowledge base. Chats are created under a
project implicitly on first send (see routes/chat.py), exactly like standalone
chats. Everything here is owner-gated (404, never 403, so ids don't leak).
"""

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_user
from src.api.db.database import get_db
from src.api.db.models import User
from src.api.schemas.schemas import (
    ProjectCreateRequest,
    ProjectUpdateRequest,
    ChatSummary,
)
from src.api.s3_bucket.s3_bucket import get_s3_client
from src.api.services import project_service
from src.api.services.project_deletion_service import delete_project

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("")
async def create_project(
    req: ProjectCreateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a project. The returned id is used as the shared RAG namespace for
    every document uploaded in any of the project's chats."""
    project = await project_service.create_project(
        db, user.id, req.name, req.description
    )
    return project_service.to_summary(project)


@router.get("")
async def list_projects(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    projects = await project_service.list_projects(db, user.id)
    return [project_service.to_summary(p) for p in projects]


@router.get("/{project_id}")
async def get_project(
    project_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await project_service.get_owned_project(db, project_id, user.id)
    return project_service.to_summary(project)


@router.patch("/{project_id}")
async def update_project(
    project_id: str,
    req: ProjectUpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await project_service.get_owned_project(db, project_id, user.id)
    project = await project_service.update_project(
        db, project, req.name, req.description
    )
    return project_service.to_summary(project)


@router.get("/{project_id}/chats")
async def list_project_chats(
    project_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Chats inside the project (owner-gated via the project lookup)."""
    await project_service.get_owned_project(db, project_id, user.id)
    chats = await project_service.list_project_chats(db, project_id)
    return [
        ChatSummary(id=c.id, title=c.title, updated_at=str(c.updated_at))
        for c in chats
    ]


@router.delete("/{project_id}")
async def remove_project(
    project_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    s3=Depends(get_s3_client),
):
    """Delete a project and everything its chats share: the shared Pinecone
    namespace, all the S3 files behind its docs, every chat (messages +
    checkpointer thread + attachment records), and the project row itself."""
    await project_service.get_owned_project(db, project_id, user.id)
    return await delete_project(project_id, user.id, db, s3)
