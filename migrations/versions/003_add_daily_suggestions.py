"""add daily_suggestions table

Revision ID: 003_daily_suggestions
Revises: 002_add_terms
Create Date: 2025-09-17
"""

from alembic import op
import sqlalchemy as sa


revision = '003_daily_suggestions'
down_revision = '002_add_terms'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'daily_suggestions',
        sa.Column('id', sa.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', sa.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('date', sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column('suggestions', sa.dialects.postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('idx_daily_suggestions_user_date', 'daily_suggestions', ['user_id', 'date'])
    op.create_unique_constraint('uq_daily_suggestions_user_date', 'daily_suggestions', ['user_id', 'date'])


def downgrade() -> None:
    op.drop_constraint('uq_daily_suggestions_user_date', 'daily_suggestions', type_='unique')
    op.drop_index('idx_daily_suggestions_user_date', table_name='daily_suggestions')
    op.drop_table('daily_suggestions')


