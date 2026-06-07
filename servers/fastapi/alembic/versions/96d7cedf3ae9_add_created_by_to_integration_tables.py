"""add created_by to integration tables

Revision ID: 96d7cedf3ae9
Revises: 5056b9c6c9cf
Create Date: 2026-06-08

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '96d7cedf3ae9'
down_revision: Union[str, None] = '5056b9c6c9cf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    if table_name not in inspector.get_table_names():
        return False
    return column_name in {c["name"] for c in inspector.get_columns(table_name)}


def upgrade() -> None:
    if not _has_column('integration_data_sources', 'created_by'):
        op.add_column(
            'integration_data_sources',
            sa.Column('created_by', sa.String(36), nullable=True),
        )
    if not _has_column('integration_credentials', 'created_by'):
        op.add_column(
            'integration_credentials',
            sa.Column('created_by', sa.String(36), nullable=True),
        )


def downgrade() -> None:
    if _has_column('integration_credentials', 'created_by'):
        op.drop_column('integration_credentials', 'created_by')
    if _has_column('integration_data_sources', 'created_by'):
        op.drop_column('integration_data_sources', 'created_by')
