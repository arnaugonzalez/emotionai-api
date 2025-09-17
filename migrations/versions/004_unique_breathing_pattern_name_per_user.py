"""unique breathing pattern name per user

Revision ID: 004_unique_pattern
Revises: 003_daily_suggestions
Create Date: 2025-09-17
"""

from alembic import op
import sqlalchemy as sa


revision = '004_unique_pattern'
down_revision = '003_daily_suggestions'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint(
        'uq_breathing_pattern_user_name',
        'breathing_patterns',
        ['user_id', 'name']
    )


def downgrade() -> None:
    op.drop_constraint('uq_breathing_pattern_user_name', 'breathing_patterns', type_='unique')


