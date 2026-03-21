"""
Integration test for pgvector migration 005.

Verifies ORM model metadata declares embedding_vector columns on the correct
tables. Actual Alembic upgrade against a pgvector-enabled Postgres is verified
manually via docker-compose (see VALIDATION.md Manual-Only section).
"""
import pytest
from sqlalchemy import inspect as sa_inspect


def test_embedding_vector_columns_exist():
    """Verify MessageModel and EmotionalRecordModel declare embedding_vector."""
    from src.infrastructure.database.models import MessageModel, EmotionalRecordModel

    # Check MessageModel has embedding_vector column
    msg_columns = {c.name for c in MessageModel.__table__.columns}
    assert "embedding_vector" in msg_columns, (
        f"MessageModel missing embedding_vector. Columns: {msg_columns}"
    )

    # Check EmotionalRecordModel has embedding_vector column
    er_columns = {c.name for c in EmotionalRecordModel.__table__.columns}
    assert "embedding_vector" in er_columns, (
        f"EmotionalRecordModel missing embedding_vector. Columns: {er_columns}"
    )


def test_embedding_vector_columns_are_nullable():
    """Verify embedding_vector columns are nullable (NULL until M3 populates)."""
    from src.infrastructure.database.models import MessageModel, EmotionalRecordModel

    for model, name in [(MessageModel, "MessageModel"), (EmotionalRecordModel, "EmotionalRecordModel")]:
        col = model.__table__.columns["embedding_vector"]
        assert col.nullable is True, f"{name}.embedding_vector must be nullable"


def test_breathing_session_model_has_no_embedding_vector():
    """Verify BreathingSessionModel does NOT have embedding_vector (not needed)."""
    from src.infrastructure.database.models import BreathingSessionModel

    bs_columns = {c.name for c in BreathingSessionModel.__table__.columns}
    assert "embedding_vector" not in bs_columns, (
        "BreathingSessionModel should NOT have embedding_vector"
    )


def test_migration_005_file_structure():
    """Verify migration file exists and has correct revision chain."""
    import importlib
    migration = importlib.import_module("migrations.versions.005_add_embedding_vectors")

    assert migration.revision == "005_embedding_vectors"
    assert migration.down_revision == "004_unique_pattern"
    assert hasattr(migration, "upgrade")
    assert hasattr(migration, "downgrade")
