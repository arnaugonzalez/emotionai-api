"""Rename token_usage.metadata to usage_metadata

Revision ID: 004_rename_metadata
Revises: 002_breathing_patterns
Create Date: 2025-08-09
"""

from alembic import op
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = '004_rename_metadata'
down_revision = '002_breathing_patterns'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Safely rename column if it exists
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [c['name'] for c in inspector.get_columns('token_usage')]
    if 'metadata' in columns and 'usage_metadata' not in columns:
        op.alter_column('token_usage', 'metadata', new_column_name='usage_metadata')


def downgrade() -> None:
    # Revert rename if possible
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [c['name'] for c in inspector.get_columns('token_usage')]
    if 'usage_metadata' in columns and 'metadata' not in columns:
        op.alter_column('token_usage', 'usage_metadata', new_column_name='metadata')


