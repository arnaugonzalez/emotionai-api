"""Extend user profile with additional fields and therapy context

Revision ID: 005_extend_user_profile
Revises: 004_rename_metadata
Create Date: 2025-08-16 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '005_extend_user_profile'
down_revision = '004_rename_metadata'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add extended profile fields and therapy context to users table"""
    
    # Add new profile fields
    op.add_column('users', sa.Column('phone_number', sa.String(length=20), nullable=True))
    op.add_column('users', sa.Column('address', sa.Text(), nullable=True))
    op.add_column('users', sa.Column('occupation', sa.String(length=100), nullable=True))
    op.add_column('users', sa.Column('emergency_contact', sa.JSON(), nullable=True))
    op.add_column('users', sa.Column('medical_conditions', sa.JSON(), nullable=True))
    op.add_column('users', sa.Column('medications', sa.JSON(), nullable=True))
    op.add_column('users', sa.Column('therapy_goals', sa.Text(), nullable=True))
    op.add_column('users', sa.Column('preferred_communication_style', sa.String(length=50), nullable=True))
    
    # Add therapy context fields
    op.add_column('users', sa.Column('therapy_context', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('users', sa.Column('therapy_preferences', sa.JSON(), nullable=True))
    op.add_column('users', sa.Column('ai_insights', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    
    # Make first_name and last_name nullable (they were required before)
    op.alter_column('users', 'first_name', nullable=True)
    op.alter_column('users', 'last_name', nullable=True)
    
    # Add username column if it doesn't exist
    op.add_column('users', sa.Column('username', sa.String(length=100), nullable=True))
    
    # Create indexes
    op.create_index('idx_users_username', 'users', ['username'])
    op.create_index('idx_users_therapy_context', 'users', ['therapy_context'], postgresql_using='gin')


def downgrade() -> None:
    """Remove extended profile fields and therapy context from users table"""
    
    # Drop indexes
    op.drop_index('idx_users_therapy_context', table_name='users')
    op.drop_index('idx_users_username', table_name='users')
    
    # Drop therapy context fields
    op.drop_column('users', 'ai_insights')
    op.drop_column('users', 'therapy_preferences')
    op.drop_column('users', 'therapy_context')
    
    # Drop profile fields
    op.drop_column('users', 'preferred_communication_style')
    op.drop_column('users', 'therapy_goals')
    op.drop_column('users', 'medications')
    op.drop_column('users', 'medical_conditions')
    op.drop_column('users', 'emergency_contact')
    op.drop_column('users', 'occupation')
    op.drop_column('users', 'address')
    op.drop_column('users', 'phone_number')
    
    # Drop username column
    op.drop_column('users', 'username')
    
    # Make first_name and last_name required again
    op.alter_column('users', 'first_name', nullable=False)
    op.alter_column('users', 'last_name', nullable=False)
