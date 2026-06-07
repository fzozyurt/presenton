from typing import Optional
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.sql.user import UserModel
from models.sql.workspace import WorkspaceModel
from models.sql.workspace_member import WorkspaceMemberModel
from workspaces.schemas import WorkspaceCreate, WorkspaceUpdate


async def list_user_workspaces(
    session: AsyncSession, user_id: uuid.UUID
) -> list[tuple[WorkspaceModel, str]]:
    """List all workspaces a user belongs to, with their role."""
    result = await session.execute(
        select(WorkspaceModel, WorkspaceMemberModel.role)
        .join(WorkspaceMemberModel, WorkspaceMemberModel.workspace_id == WorkspaceModel.id)
        .where(WorkspaceMemberModel.user_id == user_id)
        .order_by(WorkspaceModel.created_at.desc())
    )
    return [(row.WorkspaceModel, row.role) for row in result.all()]


async def create_workspace(
    session: AsyncSession, data: WorkspaceCreate, created_by: uuid.UUID
) -> WorkspaceModel:
    workspace = WorkspaceModel(
        id=uuid.uuid4(),
        name=data.name,
        slug=data.slug,
        description=data.description,
        created_by=created_by,
    )
    session.add(workspace)
    await session.flush()

    member = WorkspaceMemberModel(
        id=uuid.uuid4(),
        workspace_id=workspace.id,
        user_id=created_by,
        role="owner",
    )
    session.add(member)
    await session.flush()

    return workspace


async def get_workspace_by_id(
    session: AsyncSession, workspace_id: uuid.UUID
) -> Optional[WorkspaceModel]:
    result = await session.execute(
        select(WorkspaceModel).where(WorkspaceModel.id == workspace_id)
    )
    return result.scalar_one_or_none()


async def update_workspace(
    session: AsyncSession, workspace_id: uuid.UUID, data: WorkspaceUpdate
) -> Optional[WorkspaceModel]:
    workspace = await get_workspace_by_id(session, workspace_id)
    if workspace is None:
        return None

    if data.name is not None:
        workspace.name = data.name
    if data.description is not None:
        workspace.description = data.description

    await session.flush()
    return workspace


async def delete_workspace(session: AsyncSession, workspace_id: uuid.UUID) -> bool:
    workspace = await get_workspace_by_id(session, workspace_id)
    if workspace is None:
        return False
    await session.delete(workspace)
    await session.flush()
    return True


async def list_workspace_members(
    session: AsyncSession, workspace_id: uuid.UUID
) -> list[tuple[WorkspaceMemberModel, UserModel]]:
    result = await session.execute(
        select(WorkspaceMemberModel, UserModel)
        .join(UserModel, UserModel.id == WorkspaceMemberModel.user_id)
        .where(WorkspaceMemberModel.workspace_id == workspace_id)
        .order_by(WorkspaceMemberModel.joined_at.asc())
    )
    return [(row.WorkspaceMemberModel, row.UserModel) for row in result.all()]


async def add_workspace_member(
    session: AsyncSession,
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
    role: str,
) -> WorkspaceMemberModel:
    existing = await session.execute(
        select(WorkspaceMemberModel).where(
            WorkspaceMemberModel.workspace_id == workspace_id,
            WorkspaceMemberModel.user_id == user_id,
        )
    )
    member = existing.scalar_one_or_none()
    if member is not None:
        member.role = role
        await session.flush()
        return member

    member = WorkspaceMemberModel(
        id=uuid.uuid4(),
        workspace_id=workspace_id,
        user_id=user_id,
        role=role,
    )
    session.add(member)
    await session.flush()
    return member


async def update_member_role(
    session: AsyncSession,
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
    role: str,
) -> bool:
    result = await session.execute(
        select(WorkspaceMemberModel).where(
            WorkspaceMemberModel.workspace_id == workspace_id,
            WorkspaceMemberModel.user_id == user_id,
        )
    )
    member = result.scalar_one_or_none()
    if member is None:
        return False
    member.role = role
    await session.flush()
    return True


async def remove_workspace_member(
    session: AsyncSession, workspace_id: uuid.UUID, user_id: uuid.UUID
) -> bool:
    result = await session.execute(
        select(WorkspaceMemberModel).where(
            WorkspaceMemberModel.workspace_id == workspace_id,
            WorkspaceMemberModel.user_id == user_id,
        )
    )
    member = result.scalar_one_or_none()
    if member is None:
        return False
    await session.delete(member)
    await session.flush()
    return True
