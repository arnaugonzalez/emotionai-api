"""Add nullable embedding_vector columns for M3 semantic search

Revision ID: 005_embedding_vectors
Revises: 004_unique_pattern
Create Date: 2026-03-19
"""
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision = '005_embedding_vectors'
down_revision = '004_unique_pattern'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable pgvector extension (idempotent)
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Add nullable embedding column to messages table
    # Vector(1536) matches OpenAI text-embedding-ada-002 output dimensions
    op.add_column('messages',
        sa.Column('embedding_vector', Vector(1536), nullable=True)
    )

    # Add nullable embedding column to emotional_records table
    op.add_column('emotional_records',
        sa.Column('embedding_vector', Vector(1536), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('emotional_records', 'embedding_vector')
    op.drop_column('messages', 'embedding_vector')
    # Do NOT drop the vector extension — other migrations or features may depend on it
