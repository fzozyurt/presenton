import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import delete

from identity.provider import is_oidc_enabled
from identity.service import get_user_by_email, user_to_profile, get_user_by_id
from models.sql.presentation_layout_code import PresentationLayoutCodeModel
from models.sql.template import TemplateModel
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


# ══════════════════════════════════════════════════════════
#  Workspace-scoped Template Endpoints
# ══════════════════════════════════════════════════════════

from pydantic import BaseModel as PydanticBaseModel
from typing import List, Optional as Opt
from datetime import datetime as dt


class TemplateSummary(PydanticBaseModel):
    id: str
    name: str
    total_layouts: Opt[int] = None
    workspace_name: Opt[str] = None
    created_by_name: Opt[str] = None


class WSTemplateSaveRequest(PydanticBaseModel):
    template_info_id: uuid.UUID
    name: str
    description: Opt[str] = None
    layouts: list[dict]


class WSTemplateCloneRequest(PydanticBaseModel):
    id: str
    name: str
    description: Opt[str] = None


class WSTemplateUpdateRequest(PydanticBaseModel):
    id: uuid.UUID
    layouts: list[dict]


async def _is_admin_user(session: AsyncSession, user_id: uuid.UUID) -> bool:
    user = await get_user_by_id(session, user_id)
    return user is not None and user.is_admin


async def _get_user_workspace_role_or_none(
    session: AsyncSession, user_id: uuid.UUID, workspace_id: uuid.UUID
) -> str | None:
    import access_control.dependencies as acd
    return await acd.get_user_workspace_role(session, user_id, workspace_id)


@PROJECTS_ROUTER.get("/{workspace_id}/templates")
async def list_workspace_templates(
    workspace_id: uuid.UUID,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
):
    _require_oidc()
    user_id = await get_current_user_id_from_request(request)

    role = await _get_user_workspace_role_or_none(session, user_id, workspace_id)
    is_admin = await _is_admin_user(session, user_id)

    if role is None and not is_admin:
        raise HTTPException(status_code=403, detail="Not a member of this workspace")

    from models.sql.workspace import WorkspaceModel as WsModel

    if is_admin:
        q = (
            select(
                TemplateModel.id,
                TemplateModel.name,
                func.count(PresentationLayoutCodeModel.id).label("total_layouts"),
                WsModel.name.label("workspace_name"),
                UserModel.name.label("created_by_name"),
            )
            .outerjoin(PresentationLayoutCodeModel, PresentationLayoutCodeModel.presentation == TemplateModel.id)
            .outerjoin(WsModel, WsModel.id == TemplateModel.workspace_id)
            .outerjoin(UserModel, UserModel.id == TemplateModel.created_by)
            .group_by(TemplateModel.id, TemplateModel.name, WsModel.name, UserModel.name)
            .order_by(TemplateModel.created_at.desc())
        )
    else:
        q = (
            select(
                TemplateModel.id,
                TemplateModel.name,
                func.count(PresentationLayoutCodeModel.id).label("total_layouts"),
                WsModel.name.label("workspace_name"),
                UserModel.name.label("created_by_name"),
            )
            .outerjoin(PresentationLayoutCodeModel, PresentationLayoutCodeModel.presentation == TemplateModel.id)
            .outerjoin(WsModel, WsModel.id == TemplateModel.workspace_id)
            .outerjoin(UserModel, UserModel.id == TemplateModel.created_by)
            .where((TemplateModel.workspace_id == workspace_id) | (TemplateModel.workspace_id.is_(None)))
            .group_by(TemplateModel.id, TemplateModel.name, WsModel.name, UserModel.name)
            .order_by(TemplateModel.created_at.desc())
        )

    result = await session.execute(q)
    rows = result.all()

    return [
        {
            "id": f"custom-{str(r[0])}",
            "name": r[1],
            "total_layouts": r[2],
            "workspace_name": r[3],
            "created_by_name": r[4],
        }
        for r in rows
    ]


@PROJECTS_ROUTER.post("/{workspace_id}/templates")
async def save_workspace_template(
    workspace_id: uuid.UUID,
    body: WSTemplateSaveRequest,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
):
    _require_oidc()
    user_id = await get_current_user_id_from_request(request)

    role = await _get_user_workspace_role_or_none(session, user_id, workspace_id)
    if role not in ("owner", "admin", "editor"):
        raise HTTPException(status_code=403, detail="Insufficient permissions to create templates")

    from models.sql.template_create_info import TemplateCreateInfoModel
    template_info = await session.get(TemplateCreateInfoModel, body.template_info_id)
    if not template_info:
        raise HTTPException(status_code=400, detail="Template info not found")

    template = TemplateModel(
        id=uuid.uuid4(),
        name=body.name,
        description=body.description,
        workspace_id=workspace_id,
        created_by=user_id,
    )
    session.add(template)

    for layout in body.layouts:
        session.add(
            PresentationLayoutCodeModel(
                presentation=template.id,
                layout_id=layout["layout_id"],
                layout_name=layout["layout_name"],
                layout_code=layout["layout_code"],
                fonts=template_info.fonts,
            )
        )

    await session.commit()
    await session.refresh(template)

    return {
        "id": str(template.id),
        "name": template.name,
        "description": template.description,
        "created_at": template.created_at.isoformat(),
    }


@PROJECTS_ROUTER.post("/{workspace_id}/templates/clone")
async def clone_workspace_template(
    workspace_id: uuid.UUID,
    body: WSTemplateCloneRequest,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
):
    _require_oidc()
    user_id = await get_current_user_id_from_request(request)

    role = await _get_user_workspace_role_or_none(session, user_id, workspace_id)
    if role not in ("owner", "admin", "editor"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    try:
        template_id_uuid = uuid.UUID(body.id.replace("custom-", ""))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid template ID")

    template = await session.get(TemplateModel, template_id_uuid)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    is_admin = await _is_admin_user(session, user_id)
    if not is_admin and template.workspace_id != workspace_id and template.workspace_id is not None:
        raise HTTPException(status_code=403, detail="Template belongs to a different workspace")

    layouts_q = await session.execute(
        select(PresentationLayoutCodeModel).where(
            PresentationLayoutCodeModel.presentation == template_id_uuid
        )
    )
    layouts_db = layouts_q.scalars().all()
    if not layouts_db:
        raise HTTPException(status_code=400, detail="No layouts found")

    new_template = TemplateModel(
        id=uuid.uuid4(),
        name=body.name,
        description=body.description if body.description else template.description,
        workspace_id=workspace_id,
        created_by=user_id,
    )
    session.add(new_template)

    for layout in layouts_db:
        session.add(
            PresentationLayoutCodeModel(
                presentation=new_template.id,
                layout_id=layout.layout_id,
                layout_name=layout.layout_name,
                layout_code=layout.layout_code,
                fonts=layout.fonts,
            )
        )

    await session.commit()
    await session.refresh(new_template)

    return {
        "id": str(new_template.id),
        "name": new_template.name,
        "description": new_template.description,
        "created_at": new_template.created_at.isoformat(),
    }


@PROJECTS_ROUTER.put("/{workspace_id}/templates/{template_id}")
async def update_workspace_template(
    workspace_id: uuid.UUID,
    template_id: uuid.UUID,
    body: WSTemplateUpdateRequest,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
):
    _require_oidc()
    user_id = await get_current_user_id_from_request(request)

    role = await _get_user_workspace_role_or_none(session, user_id, workspace_id)
    is_admin = await _is_admin_user(session, user_id)
    if role not in ("owner", "admin", "editor") and not is_admin:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    template = await session.get(TemplateModel, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    if not is_admin and template.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Template belongs to a different workspace")

    existing_layout = await session.execute(
        select(PresentationLayoutCodeModel).where(
            PresentationLayoutCodeModel.presentation == template_id
        )
    )
    existing = existing_layout.scalars().all()
    fonts = existing[0].fonts if existing else None

    await session.execute(
        delete(PresentationLayoutCodeModel).where(
            PresentationLayoutCodeModel.presentation == template_id
        )
    )

    for layout in body.layouts:
        session.add(
            PresentationLayoutCodeModel(
                presentation=template.id,
                layout_id=str(layout.get("layout_id", "")),
                layout_name=str(layout.get("layout_name", "")),
                layout_code=str(layout.get("layout_code", "")),
                fonts=fonts,
            )
        )

    await session.commit()
    return {
        "id": str(template.id),
        "name": template.name,
        "description": template.description,
        "created_at": template.created_at.isoformat(),
    }


@PROJECTS_ROUTER.delete("/{workspace_id}/templates/{template_id}")
async def delete_workspace_template(
    workspace_id: uuid.UUID,
    template_id: uuid.UUID,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
):
    _require_oidc()
    user_id = await get_current_user_id_from_request(request)

    role = await _get_user_workspace_role_or_none(session, user_id, workspace_id)
    is_admin = await _is_admin_user(session, user_id)
    if role not in ("owner", "admin") and not is_admin:
        raise HTTPException(status_code=403, detail="Only owners and admins can delete templates")

    template = await session.get(TemplateModel, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    if not is_admin and template.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Template belongs to a different workspace")

    await session.execute(
        delete(PresentationLayoutCodeModel).where(
            PresentationLayoutCodeModel.presentation == template_id
        )
    )
    await session.delete(template)
    await session.commit()
    return {"success": True}


@PROJECTS_ROUTER.get("/{workspace_id}/templates/{template_id}/layouts")
async def get_workspace_template_layouts(
    workspace_id: uuid.UUID,
    template_id: uuid.UUID,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
):
    _require_oidc()
    user_id = await get_current_user_id_from_request(request)

    role = await _get_user_workspace_role_or_none(session, user_id, workspace_id)
    is_admin = await _is_admin_user(session, user_id)
    if role is None and not is_admin:
        raise HTTPException(status_code=403, detail="Not a member of this workspace")

    template = await session.get(TemplateModel, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    if not is_admin and template.workspace_id is not None and template.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Template belongs to a different workspace")

    layouts_q = await session.execute(
        select(PresentationLayoutCodeModel).where(
            PresentationLayoutCodeModel.presentation == template_id
        )
    )
    layouts_db = layouts_q.scalars().all()

    return {
        "layouts": [
            {
                "template": str(template.id),
                "layout_id": l.layout_id,
                "layout_name": l.layout_name,
                "layout_code": l.layout_code,
                "fonts": l.fonts,
            }
            for l in layouts_db
        ],
        "template": {
            "id": str(template.id),
            "name": template.name,
            "description": template.description,
            "created_at": template.created_at.isoformat(),
        } if template else None,
    }
