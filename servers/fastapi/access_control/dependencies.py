from typing import Optional
import uuid

from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from access_control.permissions import Permission, has_permission
from identity.provider import is_oidc_enabled
from identity.tokens import get_oidc_session_token_from_request, validate_oidc_session_token
from models.sql.workspace_member import WorkspaceMemberModel
from services.database import get_async_session


async def get_user_workspace_role(
    session: AsyncSession,
    user_id: uuid.UUID,
    workspace_id: uuid.UUID,
) -> Optional[str]:
    """Get the role of a user in a workspace."""
    result = await session.execute(
        select(WorkspaceMemberModel.role).where(
            WorkspaceMemberModel.user_id == user_id,
            WorkspaceMemberModel.workspace_id == workspace_id,
        )
    )
    row = result.scalar_one_or_none()
    return row


async def get_current_workspace_id(request: Request) -> Optional[uuid.UUID]:
    """Extract workspace_id from request path or headers."""
    # Try from path: /api/v1/projects/{workspace_id}/...
    path_parts = request.url.path.split("/")
    for i, part in enumerate(path_parts):
        if part in ("projects", "workspaces") and i + 1 < len(path_parts):
            try:
                return uuid.UUID(path_parts[i + 1])
            except (ValueError, IndexError):
                pass

    # Try from header
    ws_header = request.headers.get("X-Workspace-Id")
    if ws_header:
        try:
            return uuid.UUID(ws_header)
        except ValueError:
            pass

    return None


async def require_workspace_permission(
    request: Request,
    permission: Permission,
    session: AsyncSession = Depends(get_async_session),
) -> bool:
    """Check if the current user has a specific permission in the current workspace.

    Raises HTTPException(403) if not authorized.
    Returns True if OIDC is disabled (single-user mode).
    """
    if not is_oidc_enabled():
        return True

    token = get_oidc_session_token_from_request(request)
    payload = validate_oidc_session_token(token)

    if payload is None:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user_id = uuid.UUID(payload["uid"])
    workspace_id = await get_current_workspace_id(request)

    if workspace_id is None:
        return True

    role = await get_user_workspace_role(session, user_id, workspace_id)
    if role is None:
        raise HTTPException(status_code=403, detail="Not a member of this workspace")

    if not has_permission(role, permission):
        raise HTTPException(status_code=403, detail=f"Missing permission: {permission.value}")

    request.state.workspace_id = workspace_id
    request.state.workspace_role = role
    return True
