"""
SQLAlchemy Conversation Repository Implementation

Handles persistence of conversation data for agent memory and context.
"""

import logging
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, and_, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ....domain.chat.interfaces import IAgentConversationRepository
from ....domain.chat.entities import Conversation, Message
from ...database.models import ConversationModel, MessageModel
from ....domain.chat.entities import Conversation as ConversationEntity, Message as MessageEntity

logger = logging.getLogger(__name__)


class SqlAlchemyConversationRepository(IAgentConversationRepository):
    def __init__(self, database_connection):
        self.db = database_connection

    async def save_conversation(
        self,
        user_id: uuid.UUID,
        agent_type: str,
        conversation_data: Dict[str, Any]
    ) -> str:
        """Save a conversation and return its ID"""
        try:
            # Generate title if not provided
            title = conversation_data.get('title') or f"{agent_type.title()} Session - {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}"

            conversation = ConversationModel(
                id=str(uuid.uuid4()),
                user_id=str(user_id),
                agent_type=agent_type,
                title=title,
                created_at=datetime.now(timezone.utc),
                last_message_at=datetime.now(timezone.utc),
                is_active=True
            )

            async with self.db.get_session() as session:
                session.add(conversation)
                # get_session() commits on exit; explicit commit kept for clarity
                await session.commit()
                await session.refresh(conversation)

            logger.info(f"Created conversation {conversation.id} for user {user_id}")
            # Ensure we return a string ID
            return str(conversation.id)

        except Exception as e:
            logger.error(f"Error creating conversation: {e}")
            raise

    async def add_message(
        self,
        conversation_id: str,
        user_id: uuid.UUID,
        content: str,
        message_type: str,
        metadata: Dict[str, Any] = None
    ) -> Message:
        """Add a message to a conversation"""
        try:
            message = MessageModel(
                id=str(uuid.uuid4()),
                conversation_id=conversation_id,
                user_id=str(user_id),
                content=content,
                message_type=message_type,
                message_metadata=metadata or {},
                timestamp=datetime.now(timezone.utc)
            )

            async with self.db.get_session() as session:
                session.add(message)

                # Update conversation last_message_at
                await session.execute(
                    select(ConversationModel).where(ConversationModel.id == conversation_id)
                )
                conversation = await session.scalar(
                    select(ConversationModel).where(ConversationModel.id == conversation_id)
                )
                if conversation:
                    conversation.last_message_at = datetime.now(timezone.utc)
                    conversation.message_count = await self._get_message_count(conversation_id, session)

                # get_session() commits on exit; explicit commit kept for clarity
                await session.commit()
                await session.refresh(message)

            logger.info(f"Added message {message.id} to conversation {conversation_id}")
            return self._to_message_domain(message)

        except Exception as e:
            logger.error(f"Error adding message: {e}")
            raise

    async def get_conversation_history(
        self,
        user_id: uuid.UUID,
        agent_type: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get conversation history for a user and agent type"""
        try:
            query = select(ConversationModel).where(
                and_(
                    ConversationModel.user_id == str(user_id),
                    ConversationModel.agent_type == agent_type
                )
            ).order_by(desc(ConversationModel.last_message_at))

            if limit:
                query = query.limit(limit)

            async with self.db.get_session() as session:
                result = await session.execute(query)
                conversations = result.scalars().all()

            return [
                {
                    'id': str(conv.id),
                    'user_id': conv.user_id,
                    'agent_type': conv.agent_type,
                    'title': conv.title,
                    'created_at': conv.created_at.isoformat(),
                    'last_message_at': conv.last_message_at.isoformat(),
                    'message_count': conv.message_count,
                    'is_active': conv.is_active
                }
                for conv in conversations
            ]

        except Exception as e:
            logger.error(f"Error getting conversation history: {e}")
            raise

    async def get_conversation_messages(
        self,
        conversation_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[Message]:
        """Get messages from a specific conversation"""
        try:
            query = select(MessageModel).where(
                MessageModel.conversation_id == conversation_id
            ).order_by(MessageModel.timestamp)

            if limit > 0:
                query = query.limit(limit).offset(offset)

            async with self.db.get_session() as session:
                result = await session.execute(query)
                messages = result.scalars().all()

            return [self._to_message_domain(msg) for msg in messages]

        except Exception as e:
            logger.error(f"Error getting conversation messages: {e}")
            raise

    async def get_conversation_with_messages(
        self, conversation_id: str, user_id: uuid.UUID
    ) -> Optional[Dict[str, Any]]:
        """Get conversation with eagerly loaded messages (avoids N+1)"""
        async with self.db.get_session() as session:
            result = await session.execute(
                select(ConversationModel)
                .where(
                    and_(
                        ConversationModel.id == conversation_id,
                        ConversationModel.user_id == str(user_id),
                    )
                )
                .options(selectinload(ConversationModel.messages))
            )
            conv = result.scalar_one_or_none()
            if not conv:
                return None
            return {
                "id": str(conv.id),
                "user_id": conv.user_id,
                "agent_type": conv.agent_type,
                "title": conv.title,
                "message_count": conv.message_count,
                "messages": [
                    {
                        "id": str(m.id),
                        "content": m.content,
                        "message_type": m.message_type,
                        "timestamp": m.timestamp.isoformat() if m.timestamp else None,
                    }
                    for m in conv.messages
                ],
            }

    async def get_active_conversation(
        self,
        user_id: uuid.UUID,
        agent_type: str
    ) -> Optional[Conversation]:
        """Get the active conversation for a user and agent type"""
        try:
            query = select(ConversationModel).where(
                and_(
                    ConversationModel.user_id == str(user_id),
                    ConversationModel.agent_type == agent_type,
                    ConversationModel.is_active == True
                )
            ).order_by(desc(ConversationModel.last_message_at))

            async with self.db.get_session() as session:
                result = await session.execute(query)
                conversation = result.scalar_one_or_none()

            return self._to_domain(conversation) if conversation else None

        except Exception as e:
            logger.error(f"Error getting active conversation: {e}")
            raise

    async def get_conversation_summary(
        self,
        user_id: uuid.UUID,
        agent_type: str
    ) -> Optional[str]:
        """Get a summary of the most recent conversation"""
        try:
            # Get the most recent conversation
            conversation = await self.get_active_conversation(user_id, agent_type)
            if not conversation:
                return None

            # Get recent messages from that conversation
            messages = await self.get_conversation_messages(
                conversation.id,
                limit=5
            )

            if not messages:
                return "No messages in conversation"

            # Create a simple summary
            message_count = len(messages)
            last_message = messages[-1].content[:100] + "..." if len(messages[-1].content) > 100 else messages[-1].content

            return f"Conversation with {message_count} messages. Last message: {last_message}"

        except Exception as e:
            logger.error(f"Error getting conversation summary: {e}")
            return None

    async def get_recent_context(
        self,
        user_id: uuid.UUID,
        agent_type: str,
        message_count: int = 10
    ) -> List[Message]:
        """Get recent messages for context building"""
        try:
            # Get the most recent conversation
            conversation = await self.get_active_conversation(user_id, agent_type)
            if not conversation:
                return []

            # Get recent messages from that conversation
            messages = await self.get_conversation_messages(
                conversation.id,
                limit=message_count
            )

            return messages

        except Exception as e:
            logger.error(f"Error getting recent context: {e}")
            raise

    async def close_conversation(self, conversation_id: str) -> bool:
        """Close a conversation"""
        try:
            async with self.db.get_session() as session:
                conversation = await session.scalar(
                    select(ConversationModel).where(ConversationModel.id == conversation_id)
                )

                if conversation:
                    conversation.is_active = False
                    # get_session() commits on exit; explicit commit kept for clarity
                    await session.commit()
                    logger.info(f"Closed conversation {conversation_id}")
                    return True

            return False

        except Exception as e:
            logger.error(f"Error closing conversation: {e}")
            raise

    async def _get_message_count(self, conversation_id: str, session=None) -> int:
        """Get message count for a conversation"""
        try:
            if session:
                result = await session.execute(
                    select(func.count(MessageModel.id)).where(
                        MessageModel.conversation_id == conversation_id
                    )
                )
                return result.scalar() or 0
            else:
                async with self.db.get_session() as session:
                    result = await session.execute(
                        select(func.count(MessageModel.id)).where(
                            MessageModel.conversation_id == conversation_id
                        )
                    )
                    return result.scalar() or 0
        except Exception as e:
            logger.error(f"Error getting message count: {e}")
            return 0

    def _safe_uuid_convert(self, uuid_obj) -> uuid.UUID:
        """Safely convert various UUID types to standard uuid.UUID"""
        if isinstance(uuid_obj, uuid.UUID):
            return uuid_obj
        elif hasattr(uuid_obj, '__str__'):
            return uuid.UUID(str(uuid_obj))
        else:
            raise ValueError(f"Cannot convert {type(uuid_obj)} to UUID")

    def _to_domain(self, model: ConversationModel) -> Conversation:
        """Convert SQLAlchemy model to domain entity"""
        return Conversation(
            id=model.id,
            user_id=self._safe_uuid_convert(model.user_id),
            agent_type=model.agent_type,
            title=model.title,
            created_at=model.created_at,
            last_message_at=model.last_message_at,
            message_count=model.message_count,
            is_active=model.is_active
        )

    def _to_message_domain(self, model: MessageModel) -> Message:
        """Convert SQLAlchemy message model to domain entity"""
        return Message(
            id=model.id,
            conversation_id=model.conversation_id,
            user_id=self._safe_uuid_convert(model.user_id),
            content=model.content,
            message_type=model.message_type,
            metadata=model.message_metadata,
            timestamp=model.timestamp
        )
