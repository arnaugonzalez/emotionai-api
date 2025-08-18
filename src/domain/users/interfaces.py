"""
User Repository Interfaces (feature-scoped)
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

from ..entities.user import User


class IUserRepository(ABC):
    """Interface for user data access"""

    @abstractmethod
    async def get_by_id(self, user_id: UUID) -> Optional[User]:
        """Get user by ID"""
        pass

    @abstractmethod
    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        pass

    @abstractmethod
    async def save(self, user: User) -> User:
        """Save user (create or update)"""
        pass

    @abstractmethod
    async def delete(self, user_id: UUID) -> bool:
        """Delete user"""
        pass

    @abstractmethod
    async def list_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        """List users with pagination"""
        pass

    @abstractmethod
    async def exists(self, email: str) -> bool:
        """Check if user exists by email"""
        pass


