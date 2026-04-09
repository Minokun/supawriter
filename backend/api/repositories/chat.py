# -*- coding: utf-8 -*-
"""Chat repository with session and message operations."""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, delete, func, desc
from typing import Optional, List
from datetime import datetime, timedelta
from backend.api.db.models.chat import ChatSession, ChatMessage
from backend.api.repositories.base import BaseRepository


class ChatSessionRepository(BaseRepository[ChatSession]):
    """
    Repository for ChatSession model with chat-specific operations.

    Extends BaseRepository with chat session queries for session
    management, user filtering, and model tracking.
    """

    def __init__(self, session: AsyncSession):
        """Initialize ChatSession repository."""
        super().__init__(session, ChatSession)

    async def get_by_user_id(
        self,
        user_id: int,
        offset: int = 0,
        limit: int = 100,
        model_name: Optional[str] = None
    ) -> List[ChatSession]:
        """
        Get all chat sessions for a specific user.

        Args:
            user_id: User ID
            offset: Number of records to skip
            limit: Maximum number of records to return
            model_name: Optional model filter

        Returns:
            List of ChatSession instances
        """
        filters = {"user_id": user_id}
        if model_name:
            filters["model_name"] = model_name

        return await self.list(
            filters=filters,
            offset=offset,
            limit=limit,
            order_by="created_at DESC"
        )

    async def get_recent_sessions(
        self,
        user_id: int,
        days: int = 30,
        limit: int = 50
    ) -> List[ChatSession]:
        """
        Get recent chat sessions for a user within a time range.

        Args:
            user_id: User ID
            days: Number of days to look back
            limit: Maximum sessions to return

        Returns:
            List of recent ChatSession instances
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        stmt = (
            select(self.model)
            .where(
                and_(
                    self.model.user_id == user_id,
                    self.model.created_at >= cutoff_date
                )
            )
            .order_by(desc(self.model.created_at))
            .limit(limit)
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_model(
        self,
        user_id: int,
        model_name: str,
        offset: int = 0,
        limit: int = 50
    ) -> List[ChatSession]:
        """
        Get chat sessions for a user using a specific model.

        Args:
            user_id: User ID
            model_name: Model name (e.g., "gpt-4o", "claude-3-opus")
            offset: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of ChatSession instances
        """
        return await self.get_by_user_id(user_id, offset, limit, model_name)

    async def search_by_title(
        self,
        query: str,
        user_id: int,
        limit: int = 20
    ) -> List[ChatSession]:
        """
        Search chat sessions by title (case-insensitive partial match).

        Args:
            query: Search query string
            user_id: User ID
            limit: Maximum results to return

        Returns:
            List of matching ChatSession instances
        """
        search_pattern = f"%{query}%"

        stmt = (
            select(self.model)
            .where(
                and_(
                    self.model.user_id == user_id,
                    self.model.title.ilike(search_pattern)
                )
            )
            .order_by(desc(self.model.created_at))
            .limit(limit)
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_title(
        self,
        session_id: int,
        title: str
    ) -> Optional[ChatSession]:
        """
        Update chat session title.

        Args:
            session_id: Session ID
            title: New title

        Returns:
            Updated ChatSession instance or None if not found
        """
        return await self.update(session_id, title=title)

    async def update_system_prompt(
        self,
        session_id: int,
        system_prompt: str
    ) -> Optional[ChatSession]:
        """
        Update chat session system prompt.

        Args:
            session_id: Session ID
            system_prompt: New system prompt

        Returns:
            Updated ChatSession instance or None if not found
        """
        return await self.update(session_id, system_prompt=system_prompt)

    async def count_by_user(
        self,
        user_id: int,
        model_name: Optional[str] = None
    ) -> int:
        """
        Count chat sessions for a user.

        Args:
            user_id: User ID
            model_name: Optional model filter

        Returns:
            Number of chat sessions
        """
        filters = {"user_id": user_id}
        if model_name:
            filters["model_name"] = model_name

        return await self.count(filters=filters)

    async def delete_by_user(self, user_id: int) -> int:
        """
        Delete all chat sessions for a user (cascades to messages).

        Args:
            user_id: User ID

        Returns:
            Number of sessions deleted
        """
        stmt = delete(self.model).where(self.model.user_id == user_id)
        result = await self.session.execute(stmt)
        return result.rowcount

    async def get_session_with_messages(
        self,
        session_id: int
    ) -> Optional[ChatSession]:
        """
        Get chat session with messages pre-loaded.

        Args:
            session_id: Session ID

        Returns:
            ChatSession instance with messages or None if not found
        """
        stmt = (
            select(self.model)
            .where(self.model.id == session_id)
        )

        result = await self.session.execute(stmt)
        return result.scalars().first()


class ChatMessageRepository(BaseRepository[ChatMessage]):
    """
    Repository for ChatMessage model with message-specific operations.

    Extends BaseRepository with message queries for content
    management, role filtering, and session association.
    """

    def __init__(self, session: AsyncSession):
        """Initialize ChatMessage repository."""
        super().__init__(session, ChatMessage)

    async def get_by_session_id(
        self,
        session_id: int,
        offset: int = 0,
        limit: int = 100
    ) -> List[ChatMessage]:
        """
        Get all messages for a specific chat session.

        Args:
            session_id: Chat session ID
            offset: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of ChatMessage instances ordered by creation time
        """
        stmt = (
            select(self.model)
            .where(self.model.session_id == session_id)
            .order_by(self.model.created_at.asc())
            .offset(offset)
            .limit(limit)
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_session_and_role(
        self,
        session_id: int,
        role: str,
        offset: int = 0,
        limit: int = 100
    ) -> List[ChatMessage]:
        """
        Get messages for a session with a specific role.

        Args:
            session_id: Chat session ID
            role: Message role (user, assistant, system)
            offset: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of ChatMessage instances
        """
        stmt = (
            select(self.model)
            .where(
                and_(
                    self.model.session_id == session_id,
                    self.model.role == role
                )
            )
            .order_by(self.model.created_at.asc())
            .offset(offset)
            .limit(limit)
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_user_messages(
        self,
        session_id: int,
        offset: int = 0,
        limit: int = 100
    ) -> List[ChatMessage]:
        """
        Get user messages for a session.

        Args:
            session_id: Chat session ID
            offset: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of user ChatMessage instances
        """
        return await self.get_by_session_and_role(session_id, "user", offset, limit)

    async def get_assistant_messages(
        self,
        session_id: int,
        offset: int = 0,
        limit: int = 100
    ) -> List[ChatMessage]:
        """
        Get assistant messages for a session.

        Args:
            session_id: Chat session ID
            offset: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of assistant ChatMessage instances
        """
        return await self.get_by_session_and_role(session_id, "assistant", offset, limit)

    async def get_system_messages(
        self,
        session_id: int,
        offset: int = 0,
        limit: int = 100
    ) -> List[ChatMessage]:
        """
        Get system messages for a session.

        Args:
            session_id: Chat session ID
            offset: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of system ChatMessage instances
        """
        return await self.get_by_session_and_role(session_id, "system", offset, limit)

    async def create_message(
        self,
        session_id: int,
        role: str,
        content: str,
        thinking: Optional[str] = None
    ) -> ChatMessage:
        """
        Create a new chat message.

        Args:
            session_id: Chat session ID
            role: Message role (user, assistant, system)
            content: Message content
            thinking: Optional thinking process for AI messages

        Returns:
            Created ChatMessage instance
        """
        message = ChatMessage(
            session_id=session_id,
            role=role,
            content=content,
            thinking=thinking
        )
        self.session.add(message)
        await self.session.flush()
        return message

    async def update_content(
        self,
        message_id: int,
        content: str
    ) -> Optional[ChatMessage]:
        """
        Update message content.

        Args:
            message_id: Message ID
            content: New content

        Returns:
            Updated ChatMessage instance or None if not found
        """
        return await self.update(message_id, content=content)

    async def update_thinking(
        self,
        message_id: int,
        thinking: str
    ) -> Optional[ChatMessage]:
        """
        Update message thinking process.

        Args:
            message_id: Message ID
            thinking: New thinking content

        Returns:
            Updated ChatMessage instance or None if not found
        """
        return await self.update(message_id, thinking=thinking)

    async def delete_by_session(self, session_id: int) -> int:
        """
        Delete all messages for a chat session.

        Args:
            session_id: Chat session ID

        Returns:
            Number of messages deleted
        """
        stmt = delete(self.model).where(self.model.session_id == session_id)
        result = await self.session.execute(stmt)
        return result.rowcount

    async def count_by_session(self, session_id: int) -> int:
        """
        Count messages in a chat session.

        Args:
            session_id: Chat session ID

        Returns:
            Number of messages
        """
        return await self.count(filters={"session_id": session_id})

    async def count_by_session_and_role(
        self,
        session_id: int,
        role: str
    ) -> int:
        """
        Count messages in a session by role.

        Args:
            session_id: Chat session ID
            role: Message role

        Returns:
            Number of messages with the specified role
        """
        stmt = (
            select(func.count(self.model.id))
            .where(
                and_(
                    self.model.session_id == session_id,
                    self.model.role == role
                )
            )
        )

        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def get_last_message(
        self,
        session_id: int,
        role: Optional[str] = None
    ) -> Optional[ChatMessage]:
        """
        Get the last message in a session.

        Args:
            session_id: Chat session ID
            role: Optional role filter

        Returns:
            Last ChatMessage instance or None
        """
        stmt = (
            select(self.model)
            .where(self.model.session_id == session_id)
        )

        if role:
            stmt = stmt.where(self.model.role == role)

        stmt = stmt.order_by(desc(self.model.created_at)).limit(1)

        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def search_by_content(
        self,
        query: str,
        session_id: Optional[int] = None,
        limit: int = 20
    ) -> List[ChatMessage]:
        """
        Search messages by content (case-insensitive partial match).

        Args:
            query: Search query string
            session_id: Optional session ID to filter by
            limit: Maximum results to return

        Returns:
            List of matching ChatMessage instances
        """
        search_pattern = f"%{query}%"

        stmt = select(self.model).where(self.model.content.ilike(search_pattern))

        if session_id:
            stmt = stmt.where(self.model.session_id == session_id)

        stmt = stmt.order_by(desc(self.model.created_at)).limit(limit)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())
