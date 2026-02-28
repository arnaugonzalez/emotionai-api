"""
SQLAlchemy User Repository Implementation
"""

from typing import Optional, List
from uuid import UUID

from sqlalchemy import select, func

from ...domain.users.interfaces import IUserRepository
from ...domain.entities.user import User
from ..database.connection import DatabaseConnection
from ..database.models import UserModel


def _model_to_entity(model: UserModel) -> User:
    """Map SQLAlchemy UserModel to domain User entity."""
    return User(
        id=model.id,
        email=model.email,
        hashed_password=model.hashed_password or "",
        is_active=model.is_active,
        created_at=model.created_at if hasattr(model, "created_at") and model.created_at else None,
        updated_at=model.updated_at if hasattr(model, "updated_at") and model.updated_at else None,
    )


def _entity_to_model(user: User) -> UserModel:
    """Map domain User entity to SQLAlchemy UserModel for inserts."""
    return UserModel(
        id=user.id,
        email=user.email,
        hashed_password=user.hashed_password,
        is_active=user.is_active,
        is_verified=False,
    )


class SqlAlchemyUserRepository(IUserRepository):
    """SQLAlchemy implementation of user repository"""

    def __init__(self, db_connection: DatabaseConnection):
        self.db = db_connection

    async def get_by_id(self, user_id: UUID) -> Optional[User]:
        """Get user by ID"""
        async with self.db.get_session() as session:
            result = await session.execute(
                select(UserModel).where(UserModel.id == user_id)
            )
            model = result.scalar_one_or_none()
            return _model_to_entity(model) if model else None

    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        async with self.db.get_session() as session:
            result = await session.execute(
                select(UserModel).where(UserModel.email == email)
            )
            model = result.scalar_one_or_none()
            return _model_to_entity(model) if model else None

    async def save(self, user: User) -> User:
        """Save user (create or update)"""
        async with self.db.get_session() as session:
            result = await session.execute(
                select(UserModel).where(UserModel.id == user.id)
            )
            existing = result.scalar_one_or_none()
            if existing:
                existing.email = user.email
                existing.hashed_password = user.hashed_password
                existing.is_active = user.is_active
            else:
                session.add(_entity_to_model(user))
            await session.flush()
            return user

    async def delete(self, user_id: UUID) -> bool:
        """Delete user"""
        async with self.db.get_session() as session:
            result = await session.execute(
                select(UserModel).where(UserModel.id == user_id)
            )
            model = result.scalar_one_or_none()
            if model:
                await session.delete(model)
                await session.flush()
                return True
            return False

    async def list_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        """List users with pagination"""
        async with self.db.get_session() as session:
            result = await session.execute(
                select(UserModel)
                .offset(skip)
                .limit(limit)
                .order_by(UserModel.email)
            )
            return [_model_to_entity(m) for m in result.scalars().all()]

    async def exists(self, email: str) -> bool:
        """Check if user exists by email"""
        async with self.db.get_session() as session:
            result = await session.execute(
                select(func.count()).select_from(UserModel).where(UserModel.email == email)
            )
            return result.scalar() > 0
