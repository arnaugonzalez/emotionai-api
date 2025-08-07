"""Add breathing patterns and custom emotions tables

Revision ID: add_breathing_patterns_custom_emotions
Revises: previous_migration
Create Date: 2024-01-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_breathing_patterns'
down_revision = None  # Update this to point to the previous migration
branch_labels = None
depends_on = None


def upgrade():
    """Create breathing patterns and custom emotions tables"""
    
    # Create breathing_patterns table
    op.create_table('breathing_patterns',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('inhale_seconds', sa.Integer(), nullable=False),
        sa.Column('hold_seconds', sa.Integer(), nullable=False),
        sa.Column('exhale_seconds', sa.Integer(), nullable=False),
        sa.Column('cycles', sa.Integer(), nullable=False),
        sa.Column('rest_seconds', sa.Integer(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_preset', sa.Boolean(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('tags', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('tag_confidence', sa.Float(), nullable=True),
        sa.Column('processed_for_tags', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for breathing_patterns
    op.create_index('idx_breathing_patterns_user', 'breathing_patterns', ['user_id'])
    op.create_index('idx_breathing_patterns_preset', 'breathing_patterns', ['is_preset'])
    op.create_index('idx_breathing_patterns_name', 'breathing_patterns', ['name'])
    op.create_index('idx_breathing_patterns_tags', 'breathing_patterns', ['tags'], postgresql_using='gin')
    
    # Create custom_emotions table
    op.create_table('custom_emotions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('color', sa.Integer(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('usage_count', sa.Integer(), nullable=False),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('tags', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('tag_confidence', sa.Float(), nullable=True),
        sa.Column('processed_for_tags', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'name', name='uq_user_emotion_name')
    )
    
    # Create indexes for custom_emotions
    op.create_index('idx_custom_emotions_user', 'custom_emotions', ['user_id'])
    op.create_index('idx_custom_emotions_name', 'custom_emotions', ['name'])
    op.create_index('idx_custom_emotions_tags', 'custom_emotions', ['tags'], postgresql_using='gin')
    
    # Insert default breathing patterns
    op.execute("""
        INSERT INTO breathing_patterns (id, user_id, name, inhale_seconds, hold_seconds, exhale_seconds, cycles, rest_seconds, description, is_preset, is_active, processed_for_tags)
        VALUES 
        (gen_random_uuid(), NULL, '4-7-8 Relaxation Breath', 4, 7, 8, 4, 2, 'Classic relaxation breathing pattern', true, true, false),
        (gen_random_uuid(), NULL, 'Box Breathing', 4, 4, 4, 4, 4, 'Equal breathing for focus and calm', true, true, false),
        (gen_random_uuid(), NULL, 'Calm Breath', 3, 0, 6, 5, 1, 'Simple calming breath', true, true, false),
        (gen_random_uuid(), NULL, 'Wim Hof Method', 2, 0, 2, 30, 0, 'Energizing breathing technique', true, true, false),
        (gen_random_uuid(), NULL, 'Deep Yoga Breath', 5, 2, 5, 10, 1, 'Deep yogic breathing', true, true, false);
    """)


def downgrade():
    """Drop breathing patterns and custom emotions tables"""
    
    # Drop indexes first
    op.drop_index('idx_custom_emotions_tags', table_name='custom_emotions')
    op.drop_index('idx_custom_emotions_name', table_name='custom_emotions')
    op.drop_index('idx_custom_emotions_user', table_name='custom_emotions')
    op.drop_index('idx_breathing_patterns_tags', table_name='breathing_patterns')
    op.drop_index('idx_breathing_patterns_name', table_name='breathing_patterns')
    op.drop_index('idx_breathing_patterns_preset', table_name='breathing_patterns')
    op.drop_index('idx_breathing_patterns_user', table_name='breathing_patterns')
    
    # Drop tables
    op.drop_table('custom_emotions')
    op.drop_table('breathing_patterns')
