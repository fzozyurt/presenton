"""identity_and_workspaces

Revision ID: 5056b9c6c9cf
Revises: 8a1c3d4e5f6b
Create Date: 2026-06-08

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '5056b9c6c9cf'
down_revision: Union[str, None] = '8a1c3d4e5f6b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(table_name: str) -> bool:
    return table_name in sa.inspect(op.get_bind()).get_table_names()


def _has_index(table_name: str, index_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    if table_name not in inspector.get_table_names():
        return False
    return index_name in {idx["name"] for idx in inspector.get_indexes(table_name)}


def _has_column(table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    if table_name not in inspector.get_table_names():
        return False
    return column_name in {col["name"] for col in inspector.get_columns(table_name)}


def upgrade() -> None:
    if not _has_table('users'):
        op.create_table(
            'users',
            sa.Column('id', sa.String(36), nullable=False),
            sa.Column('email', sa.String(320), nullable=False),
            sa.Column('name', sa.String(255), nullable=False),
            sa.Column('hashed_password', sa.String(256), nullable=True),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('TRUE')),
            sa.Column('is_admin', sa.Boolean(), nullable=False, server_default=sa.text('FALSE')),
            sa.Column('avatar_url', sa.String(2048), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint('id'),
        )
    if not _has_index('users', 'ix_users_email'):
        op.create_index('ix_users_email', 'users', ['email'], unique=True)

    if not _has_table('oauth_accounts'):
        op.create_table(
            'oauth_accounts',
            sa.Column('id', sa.String(36), nullable=False),
            sa.Column('user_id', sa.String(36), nullable=False),
            sa.Column('provider', sa.String(64), nullable=False),
            sa.Column('provider_user_id', sa.String(256), nullable=False),
            sa.Column('access_token', sa.String(4096), nullable=True),
            sa.Column('refresh_token', sa.String(4096), nullable=True),
            sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('id_token', sa.String(8192), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.UniqueConstraint('provider', 'provider_user_id', name='uq_oauth_provider_user'),
        )
    if not _has_index('oauth_accounts', 'ix_oauth_accounts_user_id'):
        op.create_index('ix_oauth_accounts_user_id', 'oauth_accounts', ['user_id'])

    if not _has_table('roles'):
        op.create_table(
            'roles',
            sa.Column('id', sa.String(36), nullable=False),
            sa.Column('name', sa.String(64), nullable=False),
            sa.Column('description', sa.String(512), nullable=True),
            sa.Column('permissions', sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
            sa.PrimaryKeyConstraint('id'),
        )
    if not _has_index('roles', 'ix_roles_name'):
        op.create_index('ix_roles_name', 'roles', ['name'], unique=True)

    if not _has_table('workspaces'):
        op.create_table(
            'workspaces',
            sa.Column('id', sa.String(36), nullable=False),
            sa.Column('name', sa.String(255), nullable=False),
            sa.Column('slug', sa.String(255), nullable=False),
            sa.Column('description', sa.String(1024), nullable=True),
            sa.Column('created_by', sa.String(36), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='RESTRICT'),
        )
    if not _has_index('workspaces', 'ix_workspaces_slug'):
        op.create_index('ix_workspaces_slug', 'workspaces', ['slug'], unique=True)
    if not _has_index('workspaces', 'ix_workspaces_created_by'):
        op.create_index('ix_workspaces_created_by', 'workspaces', ['created_by'])

    if not _has_table('workspace_members'):
        op.create_table(
            'workspace_members',
            sa.Column('id', sa.String(36), nullable=False),
            sa.Column('workspace_id', sa.String(36), nullable=False),
            sa.Column('user_id', sa.String(36), nullable=False),
            sa.Column('role', sa.String(64), nullable=False, server_default='viewer'),
            sa.Column('joined_at', sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
            sa.UniqueConstraint('workspace_id', 'user_id', name='uq_workspace_member'),
        )
    if not _has_index('workspace_members', 'ix_workspace_members_workspace_id'):
        op.create_index('ix_workspace_members_workspace_id', 'workspace_members', ['workspace_id'])
    if not _has_index('workspace_members', 'ix_workspace_members_user_id'):
        op.create_index('ix_workspace_members_user_id', 'workspace_members', ['user_id'])

    # Add workspace_id and created_by to existing presentations table
    if _has_table('presentations') and not _has_column('presentations', 'workspace_id'):
        op.add_column('presentations', sa.Column('workspace_id', sa.String(36), nullable=True))
        op.create_foreign_key(
            'fk_presentations_workspace_id',
            'presentations', 'workspaces', ['workspace_id'], ['id'], ondelete='SET NULL',
        )
        op.create_index('ix_presentations_workspace_id', 'presentations', ['workspace_id'])
    if _has_table('presentations') and not _has_column('presentations', 'created_by'):
        op.add_column('presentations', sa.Column('created_by', sa.String(36), nullable=True))
        op.create_foreign_key(
            'fk_presentations_created_by',
            'presentations', 'users', ['created_by'], ['id'], ondelete='SET NULL',
        )
        op.create_index('ix_presentations_created_by', 'presentations', ['created_by'])

    # Add workspace_id and created_by to existing templates table
    if _has_table('templates') and not _has_column('templates', 'workspace_id'):
        op.add_column('templates', sa.Column('workspace_id', sa.String(36), nullable=True))
        op.create_foreign_key(
            'fk_templates_workspace_id',
            'templates', 'workspaces', ['workspace_id'], ['id'], ondelete='SET NULL',
        )
        op.create_index('ix_templates_workspace_id', 'templates', ['workspace_id'])
    if _has_table('templates') and not _has_column('templates', 'created_by'):
        op.add_column('templates', sa.Column('created_by', sa.String(36), nullable=True))
        op.create_foreign_key(
            'fk_templates_created_by',
            'templates', 'users', ['created_by'], ['id'], ondelete='SET NULL',
        )
        op.create_index('ix_templates_created_by', 'templates', ['created_by'])

    # Seed default roles
    _seed_roles()


def _seed_roles() -> None:
    connection = op.get_bind()
    from sqlalchemy import text
    existing = connection.execute(
        text("SELECT name FROM roles")
    ).fetchall()
    existing_names = {row[0] for row in existing}

    default_roles = {
        'owner': ['presentation:read', 'presentation:write', 'presentation:delete', 'presentation:export',
                   'template:read', 'template:write', 'template:delete',
                   'integration:read', 'integration:write', 'integration:manage',
                   'webhook:read', 'webhook:write', 'webhook:manage',
                   'workspace:read', 'workspace:write', 'workspace:delete',
                   'member:read', 'member:write', 'member:manage'],
        'admin':  ['presentation:read', 'presentation:write', 'presentation:delete', 'presentation:export',
                   'template:read', 'template:write', 'template:delete',
                   'integration:read', 'integration:write',
                   'webhook:read', 'webhook:write',
                   'workspace:read', 'workspace:write',
                   'member:read', 'member:write'],
        'editor': ['presentation:read', 'presentation:write', 'presentation:export',
                   'template:read', 'template:write',
                   'integration:read',
                   'webhook:read',
                   'workspace:read',
                   'member:read'],
        'viewer': ['presentation:read', 'template:read', 'workspace:read', 'member:read'],
    }
    for role_name, permissions in default_roles.items():
        if role_name not in existing_names:
            import uuid, json
            connection.execute(
                text("INSERT INTO roles (id, name, description, permissions) VALUES (:id, :name, :desc, :perms)"),
                {
                    'id': str(uuid.uuid4()),
                    'name': role_name,
                    'desc': f'Default {role_name} role',
                    'perms': json.dumps(permissions),
                },
            )


def downgrade() -> None:
    # Remove FK constraints and columns from presentations
    if _has_column('presentations', 'workspace_id'):
        if _has_index('presentations', 'ix_presentations_workspace_id'):
            op.drop_index('ix_presentations_workspace_id', table_name='presentations')
        op.drop_constraint('fk_presentations_workspace_id', 'presentations', type_='foreignkey')
        op.drop_column('presentations', 'workspace_id')
    if _has_column('presentations', 'created_by'):
        if _has_index('presentations', 'ix_presentations_created_by'):
            op.drop_index('ix_presentations_created_by', table_name='presentations')
        op.drop_constraint('fk_presentations_created_by', 'presentations', type_='foreignkey')
        op.drop_column('presentations', 'created_by')

    # Remove FK constraints and columns from templates
    if _has_column('templates', 'workspace_id'):
        if _has_index('templates', 'ix_templates_workspace_id'):
            op.drop_index('ix_templates_workspace_id', table_name='templates')
        op.drop_constraint('fk_templates_workspace_id', 'templates', type_='foreignkey')
        op.drop_column('templates', 'workspace_id')
    if _has_column('templates', 'created_by'):
        if _has_index('templates', 'ix_templates_created_by'):
            op.drop_index('ix_templates_created_by', table_name='templates')
        op.drop_constraint('fk_templates_created_by', 'templates', type_='foreignkey')
        op.drop_column('templates', 'created_by')

    for tbl in ('workspace_members', 'workspaces', 'roles', 'oauth_accounts', 'users'):
        for idx_name in ('ix_workspace_members_workspace_id', 'ix_workspace_members_user_id'):
            if _has_index(tbl, idx_name):
                op.drop_index(idx_name, table_name=tbl)
        for idx_name in ('ix_workspaces_slug', 'ix_workspaces_created_by'):
            if _has_index(tbl, idx_name):
                op.drop_index(idx_name, table_name=tbl)
        for idx_name in ('ix_roles_name',):
            if _has_index(tbl, idx_name):
                op.drop_index(idx_name, table_name=tbl)
        for idx_name in ('ix_oauth_accounts_user_id',):
            if _has_index(tbl, idx_name):
                op.drop_index(idx_name, table_name=tbl)
        for idx_name in ('ix_users_email',):
            if _has_index(tbl, idx_name):
                op.drop_index(idx_name, table_name=tbl)
        if _has_table(tbl):
            op.drop_table(tbl)
