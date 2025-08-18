"""Base tables migration

Revision ID: 001_base_tables
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_base_tables'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create base tables that should exist before other migrations"""
    
    # Create users table (required by other migrations)
    op.create_table('users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False, unique=True),
        sa.Column('username', sa.String(length=100), nullable=True),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('first_name', sa.String(length=100), nullable=True),
        sa.Column('last_name', sa.String(length=100), nullable=True),
        sa.Column('date_of_birth', sa.Date(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('is_verified', sa.Boolean(), nullable=False, default=False),
        sa.Column('agent_personality_data', sa.JSON(), nullable=True),
        sa.Column('user_profile_data', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create index for users
    op.create_index('idx_users_email', 'users', ['email'])
    
    # Create conversations table (required by messages table)
    op.create_table('conversations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('agent_type', sa.String(length=50), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('context_data', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('message_count', sa.Integer(), nullable=False, default=0),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('last_message_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for conversations
    op.create_index('idx_conversations_user_agent', 'conversations', ['user_id', 'agent_type'])
    op.create_index('idx_conversations_active', 'conversations', ['is_active'])
    op.create_index('idx_conversations_last_message', 'conversations', ['last_message_at'])


def downgrade() -> None:
    """Drop base tables"""
    # Drop conversations first (due to foreign key)
    op.drop_index('idx_conversations_last_message', table_name='conversations')
    op.drop_index('idx_conversations_active', table_name='conversations')
    op.drop_index('idx_conversations_user_agent', table_name='conversations')
    op.drop_table('conversations')
    
    # Drop users table
    op.drop_index('idx_users_email', table_name='users')
    op.drop_table('users')
