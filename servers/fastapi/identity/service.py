from typing import Optional
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.sql.user import UserModel
from models.sql.oauth_account import OAuthAccountModel
from models.sql.workspace import WorkspaceModel
from models.sql.workspace_member import WorkspaceMemberModel
from identity.schemas import UserCreate, UserProfile


async def get_user_by_id(session: AsyncSession, user_id: uuid.UUID) -> Optional[UserModel]:
    result = await session.execute(select(UserModel).where(UserModel.id == user_id))
    return result.scalar_one_or_none()


async def get_user_by_email(session: AsyncSession, email: str) -> Optional[UserModel]:
    result = await session.execute(
        select(UserModel).where(UserModel.email == email.lower().strip())
    )
    return result.scalar_one_or_none()


async def get_user_by_oauth(
    session: AsyncSession, provider: str, provider_user_id: str
) -> Optional[UserModel]:
    result = await session.execute(
        select(UserModel).join(OAuthAccountModel).where(
            OAuthAccountModel.provider == provider,
            OAuthAccountModel.provider_user_id == provider_user_id,
        )
    )
    return result.scalar_one_or_none()


async def create_user(session: AsyncSession, data: UserCreate) -> UserModel:
    user = UserModel(
        id=uuid.uuid4(),
        email=data.email.lower().strip(),
        name=data.name,
        avatar_url=data.avatar_url,
        is_active=True,
        is_admin=False,
    )
    session.add(user)
    await session.flush()
    return user


async def get_or_create_user_by_oidc(
    session: AsyncSession,
    provider: str,
    provider_user_id: str,
    email: Optional[str],
    name: Optional[str],
    avatar_url: Optional[str],
    access_token: str,
    refresh_token: Optional[str],
    id_token: Optional[str],
    expires_in: Optional[int],
) -> tuple[UserModel, bool]:
    """Find or create a user by OIDC claims. Returns (user, was_created)."""
    user = await get_user_by_oauth(session, provider, provider_user_id)

    if user is not None:
        await _update_oauth_tokens(
            session, user.id, provider, access_token, refresh_token, id_token, expires_in
        )
        return user, False

    if email:
        user = await get_user_by_email(session, email)
        if user is not None:
            await _link_oauth_account(
                session, user.id, provider, provider_user_id,
                access_token, refresh_token, id_token, expires_in,
            )
            return user, False

    user = await create_user(
        session,
        UserCreate(email=email or f"{provider_user_id}@{provider}.oidc", name=name or provider_user_id, avatar_url=avatar_url),
    )
    await _link_oauth_account(
        session, user.id, provider, provider_user_id,
        access_token, refresh_token, id_token, expires_in,
    )

    # First user in the system → auto-admin + default workspace
    await _bootstrap_first_admin(session, user, email)

    return user, True


async def _link_oauth_account(
    session: AsyncSession,
    user_id: uuid.UUID,
    provider: str,
    provider_user_id: str,
    access_token: str,
    refresh_token: Optional[str],
    id_token: Optional[str],
    expires_in: Optional[int],
) -> None:
    from datetime import datetime, timezone, timedelta

    expires_at = None
    if expires_in:
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

    oauth_account = OAuthAccountModel(
        id=uuid.uuid4(),
        user_id=user_id,
        provider=provider,
        provider_user_id=provider_user_id,
        access_token=access_token,
        refresh_token=refresh_token,
        id_token=id_token,
        expires_at=expires_at,
    )
    session.add(oauth_account)
    await session.flush()


async def _update_oauth_tokens(
    session: AsyncSession,
    user_id: uuid.UUID,
    provider: str,
    access_token: str,
    refresh_token: Optional[str],
    id_token: Optional[str],
    expires_in: Optional[int],
) -> None:
    from datetime import datetime, timezone, timedelta

    result = await session.execute(
        select(OAuthAccountModel).where(
            OAuthAccountModel.user_id == user_id,
            OAuthAccountModel.provider == provider,
        )
    )
    oauth_account = result.scalar_one_or_none()
    if oauth_account is None:
        return

    oauth_account.access_token = access_token
    if refresh_token:
        oauth_account.refresh_token = refresh_token
    if id_token:
        oauth_account.id_token = id_token

    if expires_in:
        oauth_account.expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

    await session.flush()


async def _bootstrap_first_admin(session: AsyncSession, user: UserModel, email: Optional[str]) -> None:
    """Make the first user admin + create default workspace if users table was empty."""
    import os

    count = await session.scalar(select(func.count()).select_from(UserModel))
    if count != 1:
        return  # not the first user

    initial_admin = (os.getenv("INITIAL_ADMIN_EMAIL") or "").strip().lower()
    if initial_admin and email and email.lower() != initial_admin:
        return  # INITIAL_ADMIN_EMAIL set but doesn't match

    user.is_admin = True
    session.add(user)

    ws = WorkspaceModel(
        id=uuid.uuid4(),
        name="Default Workspace",
        slug="default",
        description="Auto-created default workspace",
        created_by=user.id,
    )
    session.add(ws)
    await session.flush()

    member = WorkspaceMemberModel(
        id=uuid.uuid4(),
        workspace_id=ws.id,
        user_id=user.id,
        role="owner",
    )
    session.add(member)
    await session.flush()


def user_to_profile(user: UserModel) -> UserProfile:
    return UserProfile(
        id=user.id,
        email=user.email,
        name=user.name,
        avatar_url=user.avatar_url,
        is_admin=user.is_admin,
        is_active=user.is_active,
    )
