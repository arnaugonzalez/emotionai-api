"""add terms_accepted columns to users

Revision ID: 002_add_terms
Revises: 001_initial_schema
Create Date: 2025-09-17
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '002_add_terms'
down_revision = '001_initial_schema'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('terms_accepted', sa.Boolean(), nullable=False, server_default=sa.text('false')))
    op.add_column('users', sa.Column('terms_accepted_at', sa.DateTime(timezone=True), nullable=True))
    # Drop server_default after backfilling default value
    op.alter_column('users', 'terms_accepted', server_default=None)


def downgrade() -> None:
    op.drop_column('users', 'terms_accepted_at')
    op.drop_column('users', 'terms_accepted')


