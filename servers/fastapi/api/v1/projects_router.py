import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from identity.provider import is_oidc_enabled
from identity.service import get_user_by_email, user_to_profile
from models.sql.user import UserModel
from services.database import get_async_session
from workspaces.dependencies import get_current_user_id_from_request
from workspaces.schemas import (
    WorkspaceCreate,
    WorkspaceUpdate,
    WorkspaceResponse,
    WorkspaceMemberResponse,
    MemberCreate,
    MemberUpdate,
)
from workspaces.service import (
    list_user_workspaces,
    create_workspace,
    get_workspace_by_id,
    update_workspace,
    delete_workspace,
    list_workspace_members,
    add_workspace_member,
    update_member_role,
    remove_workspace_member,
)

PROJECTS_ROUTER = APIRouter(prefix="/api/v1/projects", tags=["Workspaces"])


def _require_oidc():
    if not is_oidc_enabled():
        raise HTTPException(status_code=400, detail="OIDC is not enabled")


def _ws_to_response(ws, role: str) -> dict:
    return {
        "id": str(ws.id),
        "name": ws.name,
        "slug": ws.slug,
        "description": ws.description,
        "created_by": str(ws.created_by),
        "created_at": ws.created_at.isoformat(),
        "updated_at": ws.updated_at.isoformat(),
        "role": role,
    }


@PROJECTS_ROUTER.get("/")
async def list_projects(
    request: Request,
    session: AsyncSession = Depends(get_async_session),
):
    _require_oidc()
    user_id = await get_current_user_id_from_request(request)
    results = await list_user_workspaces(session, user_id)
    return [_ws_to_response(ws, role) for ws, role in results]


@PROJECTS_ROUTER.post("/")
async def create_project(
    body: WorkspaceCreate,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
):
    _require_oidc()
    user_id = await get_current_user_id_from_request(request)
    workspace = await create_workspace(session, body, user_id)
    await session.commit()
    return _ws_to_response(workspace, "owner")


@PROJECTS_ROUTER.get("/{workspace_id}")
async def get_project(
    workspace_id: uuid.UUID,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
):
    _require_oidc()
    user_id = await get_current_user_id_from_request(request)
    ws = await get_workspace_by_id(session, workspace_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="Workspace not found")

    # Check membership
    role = None
    import access_control.dependencies as acd
    role = await acd.get_user_workspace_role(session, user_id, workspace_id)
    if role is None:
        raise HTTPException(status_code=403, detail="Not a member of this workspace")

    return _ws_to_response(ws, role)


@PROJECTS_ROUTER.put("/{workspace_id}")
async def update_project(
    workspace_id: uuid.UUID,
    body: WorkspaceUpdate,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
):
    _require_oidc()
    user_id = await get_current_user_id_from_request(request)
    import access_control.dependencies as acd
    role = await acd.get_user_workspace_role(session, user_id, workspace_id)
    if role not in ("owner", "admin"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    ws = await update_workspace(session, workspace_id, body)
    if ws is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    await session.commit()
    return _ws_to_response(ws, role)


@PROJECTS_ROUTER.delete("/{workspace_id}")
async def delete_project(
    workspace_id: uuid.UUID,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
):
    _require_oidc()
    user_id = await get_current_user_id_from_request(request)
    import access_control.dependencies as acd
    role = await acd.get_user_workspace_role(session, user_id, workspace_id)
    if role != "owner":
        raise HTTPException(status_code=403, detail="Only owners can delete a workspace")

    success = await delete_workspace(session, workspace_id)
    if not success:
        raise HTTPException(status_code=404, detail="Workspace not found")
    await session.commit()
    return {"success": True}


@PROJECTS_ROUTER.get("/{workspace_id}/members")
async def list_members(
    workspace_id: uuid.UUID,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
):
    _require_oidc()
    user_id = await get_current_user_id_from_request(request)
    import access_control.dependencies as acd
    role = await acd.get_user_workspace_role(session, user_id, workspace_id)
    if role is None:
        raise HTTPException(status_code=403, detail="Not a member of this workspace")

    members = await list_workspace_members(session, workspace_id)
    return [
        {
            "id": str(member.id),
            "user_id": str(user.id),
            "user_name": user.name,
            "user_email": user.email,
            "user_avatar": user.avatar_url,
            "role": member.role,
            "joined_at": member.joined_at.isoformat(),
        }
        for member, user in members
    ]


@PROJECTS_ROUTER.post("/{workspace_id}/members")
async def add_member(
    workspace_id: uuid.UUID,
    body: MemberCreate,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
):
    _require_oidc()
    inviter_id = await get_current_user_id_from_request(request)
    import access_control.dependencies as acd
    inviter_role = await acd.get_user_workspace_role(session, inviter_id, workspace_id)
    if inviter_role not in ("owner", "admin"):
        raise HTTPException(status_code=403, detail="Only owners and admins can add members")

    target_user = await get_user_by_email(session, body.email)
    if target_user is None:
        raise HTTPException(status_code=404, detail="User not found")

    member = await add_workspace_member(session, workspace_id, target_user.id, body.role)
    await session.commit()
    return {
        "id": str(member.id),
        "user_id": str(target_user.id),
        "user_name": target_user.name,
        "user_email": target_user.email,
        "role": member.role,
        "joined_at": member.joined_at.isoformat(),
    }


@PROJECTS_ROUTER.put("/{workspace_id}/members/{member_user_id}")
async def update_member(
    workspace_id: uuid.UUID,
    member_user_id: uuid.UUID,
    body: MemberUpdate,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
):
    _require_oidc()
    user_id = await get_current_user_id_from_request(request)
    import access_control.dependencies as acd
    role = await acd.get_user_workspace_role(session, user_id, workspace_id)
    if role not in ("owner", "admin"):
        raise HTTPException(status_code=403, detail="Only owners and admins can change roles")

    success = await update_member_role(session, workspace_id, member_user_id, body.role)
    if not success:
        raise HTTPException(status_code=404, detail="Member not found")
    await session.commit()
    return {"success": True}


@PROJECTS_ROUTER.delete("/{workspace_id}/members/{member_user_id}")
async def remove_member(
    workspace_id: uuid.UUID,
    member_user_id: uuid.UUID,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
):
    _require_oidc()
    user_id = await get_current_user_id_from_request(request)
    import access_control.dependencies as acd
    role = await acd.get_user_workspace_role(session, user_id, workspace_id)
    if role not in ("owner", "admin"):
        raise HTTPException(status_code=403, detail="Only owners and admins can remove members")

    success = await remove_workspace_member(session, workspace_id, member_user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Member not found")
    await session.commit()
    return {"success": True}
