"""Add conversation and message tables

Revision ID: 001_conversations
Revises: 001_base_tables
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_conversations'
down_revision = '001_base_tables'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create messages table (conversations table already exists from base migration)
    op.create_table('messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('conversation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('message_type', sa.String(length=20), nullable=False),
        sa.Column('message_metadata', sa.JSON(), nullable=True),
        sa.Column('tags', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('tag_confidence', sa.Float(), nullable=True),
        sa.Column('processed_for_tags', sa.Boolean(), nullable=False, default=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for messages
    op.create_index('idx_messages_conversation', 'messages', ['conversation_id'])
    op.create_index('idx_messages_user', 'messages', ['user_id'])
    op.create_index('idx_messages_type', 'messages', ['message_type'])
    op.create_index('idx_messages_timestamp', 'messages', ['timestamp'])
    op.create_index('idx_messages_tags', 'messages', ['tags'], postgresql_using='gin')


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_messages_tags', table_name='messages')
    op.drop_index('idx_messages_timestamp', table_name='messages')
    op.drop_index('idx_messages_type', table_name='messages')
    op.drop_index('idx_messages_user', table_name='messages')
    op.drop_index('idx_messages_conversation', table_name='messages')
    
    # Drop messages table (conversations table is handled by base migration)
    op.drop_table('messages')
