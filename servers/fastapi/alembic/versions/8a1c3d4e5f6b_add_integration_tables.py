"""add_integration_tables

Revision ID: 8a1c3d4e5f6b
Revises: c7b70d0f31b1
Create Date: 2026-06-07

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '8a1c3d4e5f6b'
down_revision: Union[str, None] = 'c7b70d0f31b1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(table_name: str) -> bool:
    return table_name in sa.inspect(op.get_bind()).get_table_names()


def _has_index(table_name: str, index_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    if table_name not in inspector.get_table_names():
        return False
    return index_name in {idx["name"] for idx in inspector.get_indexes(table_name)}


def upgrade() -> None:
    if not _has_table('integration_credentials'):
        op.create_table(
            'integration_credentials',
            sa.Column('id', sa.String(255), nullable=False),
            sa.Column('module', sa.String(64), nullable=False),
            sa.Column('type', sa.String(64), nullable=False),
            sa.Column('status', sa.String(32), nullable=False, server_default='active'),
            sa.Column('label', sa.String(255), nullable=True),
            sa.Column('key_id', sa.String(32), nullable=False),
            sa.Column('fingerprint', sa.String(32), nullable=False),
            sa.Column('encrypted_secret', sa.String(4096), nullable=False),
            sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint('id'),
        )
    if not _has_index('integration_credentials', 'ix_integration_credentials_module'):
        op.create_index('ix_integration_credentials_module', 'integration_credentials', ['module'])
    if not _has_index('integration_credentials', 'ix_integration_credentials_type'):
        op.create_index('ix_integration_credentials_type', 'integration_credentials', ['type'])

    if not _has_table('integration_data_sources'):
        op.create_table(
            'integration_data_sources',
            sa.Column('id', sa.String(255), nullable=False),
            sa.Column('type', sa.String(64), nullable=False),
            sa.Column('name', sa.String(255), nullable=False),
            sa.Column('credential_ref', sa.String(255), nullable=True),
            sa.Column('base_config', sa.JSON(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint('id'),
        )
    if not _has_index('integration_data_sources', 'ix_integration_data_sources_type'):
        op.create_index('ix_integration_data_sources_type', 'integration_data_sources', ['type'])

    if not _has_table('integration_bindings'):
        op.create_table(
            'integration_bindings',
            sa.Column('id', sa.String(255), nullable=False),
            sa.Column('presentation_id', sa.String(36), nullable=False),
            sa.Column('datasource_id', sa.String(64), nullable=False),
            sa.Column('alias', sa.String(255), nullable=True),
            sa.Column('binding_config', sa.JSON(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint('id'),
        )
    if not _has_index('integration_bindings', 'ix_integration_bindings_presentation_id'):
        op.create_index('ix_integration_bindings_presentation_id', 'integration_bindings', ['presentation_id'])
    if not _has_index('integration_bindings', 'ix_integration_bindings_datasource_id'):
        op.create_index('ix_integration_bindings_datasource_id', 'integration_bindings', ['datasource_id'])

    if not _has_table('integration_report_runs'):
        op.create_table(
            'integration_report_runs',
            sa.Column('id', sa.String(255), nullable=False),
            sa.Column('presentation_id', sa.String(36), nullable=False),
            sa.Column('binding_id', sa.String(64), nullable=True),
            sa.Column('status', sa.String(32), nullable=False, server_default='pending'),
            sa.Column('error_message', sa.Text(), nullable=True),
            sa.Column('result_data', sa.JSON(), nullable=True),
            sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint('id'),
        )
    if not _has_index('integration_report_runs', 'ix_integration_report_runs_presentation_id'):
        op.create_index('ix_integration_report_runs_presentation_id', 'integration_report_runs', ['presentation_id'])


def downgrade() -> None:
    for tbl in ('integration_report_runs', 'integration_bindings', 'integration_data_sources', 'integration_credentials'):
        for idx_name in ('ix_integration_report_runs_presentation_id',):
            if _has_index(tbl, idx_name):
                op.drop_index(idx_name, table_name=tbl)
        for idx_name in ('ix_integration_bindings_presentation_id', 'ix_integration_bindings_datasource_id'):
            if _has_index(tbl, idx_name):
                op.drop_index(idx_name, table_name=tbl)
        for idx_name in ('ix_integration_data_sources_type',):
            if _has_index(tbl, idx_name):
                op.drop_index(idx_name, table_name=tbl)
        for idx_name in ('ix_integration_credentials_module', 'ix_integration_credentials_type'):
            if _has_index(tbl, idx_name):
                op.drop_index(idx_name, table_name=tbl)
        if _has_table(tbl):
            op.drop_table(tbl)
