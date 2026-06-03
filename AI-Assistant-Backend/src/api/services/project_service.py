"""Project CRUD — the workspace layer that groups chats over a shared RAG corpus.

A project is created up front with a name + description; its generated `id`
becomes the Pinecone namespace for every document uploaded in any of its chats
(see services/namespace.py). These helpers are pure persistence; the heavy
teardown on delete lives in `project_deletion_service.py`.
"""

import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.api.db.models import Project, Chat, now_utc
from src.api.exceptions import NotFoundError

logger = logging.getLogger(__name__)


def to_summary(p: Project) -> dict:
    """Serialize a Project to the response shape the frontend consumes."""
    return {
        "id": p.id,
        "name": p.name,
        "description": p.description,
        "created_at": str(p.created_at),
        "updated_at": str(p.updated_at),
    }


async def create_project(db: AsyncSession, user_id: str, name: str,
                         description: str) -> Project:
    """Create a project owned by `user_id`. Its id is the shared RAG namespace."""
    project = Project(user_id=user_id, name=name.strip() or "Untitled project",
                      description=description.strip())
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return project


async def list_projects(db: AsyncSession, user_id: str) -> list[Project]:
    """The caller's projects, most-recently-updated first."""
    res = await db.execute(
        select(Project)
        .where(Project.user_id == user_id)
        .order_by(Project.updated_at.desc())
    )
    return list(res.scalars().all())


async def get_owned_project(db: AsyncSession, project_id: str,
                            user_id: str) -> Project:
    """Fetch a project, 404ing unless it exists AND belongs to the caller (same
    no-leak gate the chat read paths use)."""
    res = await db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == user_id)
    )
    project = res.scalar_one_or_none()
    if project is None:
        raise NotFoundError(detail="Project not found")
    return project


async def update_project(db: AsyncSession, project: Project,
                         name: str | None, description: str | None) -> Project:
    """Patch a project's name/description (only the provided fields)."""
    if name is not None:
        project.name = name.strip() or project.name
    if description is not None:
        project.description = description.strip()
    project.updated_at = now_utc()
    await db.commit()
    await db.refresh(project)
    return project


async def list_project_chats(db: AsyncSession, project_id: str) -> list[Chat]:
    """Chats inside a project, most-recently-updated first. Caller must have
    already verified project ownership."""
    res = await db.execute(
        select(Chat)
        .where(Chat.project_id == project_id)
        .order_by(Chat.updated_at.desc())
    )
    return list(res.scalars().all())
