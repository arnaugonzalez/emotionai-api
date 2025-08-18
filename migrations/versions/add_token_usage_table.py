"""create token_usage table

Revision ID: 003_token_usage
Revises: 001_conversations
Create Date: 2025-08-07
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '003_token_usage'
down_revision = '001_conversations'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'token_usage',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('interaction_type', sa.String(length=50), nullable=False),
        sa.Column('model', sa.String(length=100), nullable=True),
        sa.Column('data_id', sa.String(length=100), nullable=True),
        sa.Column('tokens_total', sa.Integer(), nullable=False),
        sa.Column('tokens_prompt', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('tokens_completion', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
    )
    op.create_index('idx_token_usage_user_created', 'token_usage', ['user_id', 'created_at'])
    op.create_index('idx_token_usage_type', 'token_usage', ['interaction_type'])


def downgrade() -> None:
    op.drop_index('idx_token_usage_type', table_name='token_usage')
    op.drop_index('idx_token_usage_user_created', table_name='token_usage')
    op.drop_table('token_usage')


