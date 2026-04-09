# -*- coding: utf-8 -*-
"""Chat service with conversation management and AI interaction logic."""
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Dict, List
from datetime import datetime
from backend.api.db.models.chat import ChatSession, ChatMessage
from backend.api.repositories.chat import ChatSessionRepository, ChatMessageRepository
from backend.api.repositories.config import UserModelConfigRepository


class ChatService:
    """
    Service layer for chat operations.

    Handles business logic for chat session management, message
    handling, model configuration, and conversation context.
    """

    def __init__(
        self,
        session: AsyncSession,
        session_repository: ChatSessionRepository,
        message_repository: ChatMessageRepository,
        model_config_repository: Optional[UserModelConfigRepository] = None
    ):
        """
        Initialize ChatService.

        Args:
            session: Database session
            session_repository: Chat session repository instance
            message_repository: Chat message repository instance
            model_config_repository: Optional model config repository
        """
        self.session = session
        self.session_repo = session_repository
        self.message_repo = message_repository
        self.model_config_repo = model_config_repository

    async def create_chat_session(
        self,
        user_id: int,
        title: str = "New Chat",
        model_name: str = "gpt-4o",
        system_prompt: Optional[str] = None
    ) -> ChatSession:
        """
        Create a new chat session.

        Args:
            user_id: User ID
            title: Chat session title
            model_name: AI model to use
            system_prompt: Optional system prompt for the AI

        Returns:
            Created ChatSession instance
        """
        session = await self.session_repo.create(
            user_id=user_id,
            title=title,
            model_name=model_name,
            system_prompt=system_prompt
        )
        return session

    async def get_session_with_messages(
        self,
        session_id: int,
        user_id: int
    ) -> Optional[Dict]:
        """
        Get chat session with all messages and access verification.

        Args:
            session_id: Chat session ID
            user_id: User ID (for access verification)

        Returns:
            Dictionary with session and messages or None if not found/no access
        """
        session = await self.session_repo.get_by_id(session_id)
        if not session or session.user_id != user_id:
            return None

        messages = await self.message_repo.get_by_session_id(session_id)

        return {
            "id": session.id,
            "user_id": session.user_id,
            "title": session.title,
            "model_name": session.model_name,
            "system_prompt": session.system_prompt,
            "created_at": session.created_at,
            "updated_at": session.updated_at,
            "messages": [
                {
                    "id": msg.id,
                    "role": msg.role,
                    "content": msg.content,
                    "thinking": msg.thinking,
                    "created_at": msg.created_at
                }
                for msg in messages
            ]
        }

    async def add_user_message(
        self,
        session_id: int,
        user_id: int,
        content: str
    ) -> Optional[ChatMessage]:
        """
        Add a user message to a chat session.

        Args:
            session_id: Chat session ID
            user_id: User ID (for access verification)
            content: Message content

        Returns:
            Created ChatMessage instance or None if session not found/no access
        """
        # Verify session ownership
        session = await self.session_repo.get_by_id(session_id)
        if not session or session.user_id != user_id:
            return None

        # Create message
        message = await self.message_repo.create_message(
            session_id=session_id,
            role="user",
            content=content
        )

        return message

    async def add_assistant_message(
        self,
        session_id: int,
        content: str,
        thinking: Optional[str] = None
    ) -> Optional[ChatMessage]:
        """
        Add an assistant message to a chat session.

        Args:
            session_id: Chat session ID
            content: Message content
            thinking: Optional AI thinking process

        Returns:
            Created ChatMessage instance or None if session not found
        """
        # Verify session exists
        session = await self.session_repo.get_by_id(session_id)
        if not session:
            return None

        # Create message
        message = await self.message_repo.create_message(
            session_id=session_id,
            role="assistant",
            content=content,
            thinking=thinking
        )

        return message

    async def add_system_message(
        self,
        session_id: int,
        content: str
    ) -> Optional[ChatMessage]:
        """
        Add a system message to a chat session.

        Args:
            session_id: Chat session ID
            content: Message content

        Returns:
            Created ChatMessage instance or None if session not found
        """
        # Verify session exists
        session = await self.session_repo.get_by_id(session_id)
        if not session:
            return None

        # Create message
        message = await self.message_repo.create_message(
            session_id=session_id,
            role="system",
            content=content
        )

        return message

    async def get_conversation_context(
        self,
        session_id: int,
        user_id: int,
        include_system: bool = True,
        max_messages: int = 50
    ) -> Optional[List[Dict]]:
        """
        Get formatted conversation context for AI processing.

        Args:
            session_id: Chat session ID
            user_id: User ID (for access verification)
            include_system: Include system prompt
            max_messages: Maximum messages to include

        Returns:
            List of message dictionaries or None if no access
        """
        # Verify session ownership
        session = await self.session_repo.get_by_id(session_id)
        if not session or session.user_id != user_id:
            return None

        messages = await self.message_repo.get_by_session_id(
            session_id,
            limit=max_messages
        )

        context = []

        # Add system prompt if requested
        if include_system and session.system_prompt:
            context.append({
                "role": "system",
                "content": session.system_prompt
            })

        # Add messages
        for msg in messages:
            context.append({
                "role": msg.role,
                "content": msg.content
            })

        return context

    async def update_session_title(
        self,
        session_id: int,
        user_id: int,
        title: str
    ) -> Optional[ChatSession]:
        """
        Update chat session title.

        Args:
            session_id: Chat session ID
            user_id: User ID (for access verification)
            title: New title

        Returns:
            Updated ChatSession instance or None if not found/no access
        """
        # Verify session ownership
        session = await self.session_repo.get_by_id(session_id)
        if not session or session.user_id != user_id:
            return None

        return await self.session_repo.update_title(session_id, title)

    async def update_system_prompt(
        self,
        session_id: int,
        user_id: int,
        system_prompt: str
    ) -> Optional[ChatSession]:
        """
        Update chat session system prompt.

        Args:
            session_id: Chat session ID
            user_id: User ID (for access verification)
            system_prompt: New system prompt

        Returns:
            Updated ChatSession instance or None if not found/no access
        """
        # Verify session ownership
        session = await self.session_repo.get_by_id(session_id)
        if not session or session.user_id != user_id:
            return None

        return await self.session_repo.update_system_prompt(session_id, system_prompt)

    async def delete_session(
        self,
        session_id: int,
        user_id: int
    ) -> bool:
        """
        Delete a chat session with all messages.

        Args:
            session_id: Chat session ID
            user_id: User ID (for ownership verification)

        Returns:
            True if deleted, False if not found/not owned
        """
        # Verify session ownership
        session = await self.session_repo.get_by_id(session_id)
        if not session or session.user_id != user_id:
            return False

        # Delete messages first (cascade should handle this, but being explicit)
        await self.message_repo.delete_by_session(session_id)

        # Delete session
        await self.session_repo.delete(session_id)
        return True

    async def get_user_sessions(
        self,
        user_id: int,
        model_name: Optional[str] = None,
        offset: int = 0,
        limit: int = 20
    ) -> List[ChatSession]:
        """
        Get chat sessions for a user.

        Args:
            user_id: User ID
            model_name: Optional model filter
            offset: Pagination offset
            limit: Pagination limit

        Returns:
            List of ChatSession instances
        """
        return await self.session_repo.get_by_user_id(
            user_id=user_id,
            offset=offset,
            limit=limit,
            model_name=model_name
        )

    async def get_recent_sessions(
        self,
        user_id: int,
        days: int = 30,
        limit: int = 10
    ) -> List[ChatSession]:
        """
        Get recent chat sessions for a user.

        Args:
            user_id: User ID
            days: Number of days to look back
            limit: Maximum sessions to return

        Returns:
            List of recent ChatSession instances
        """
        return await self.session_repo.get_recent_sessions(user_id, days, limit)

    async def search_sessions(
        self,
        query: str,
        user_id: int,
        limit: int = 20
    ) -> List[ChatSession]:
        """
        Search chat sessions by title.

        Args:
            query: Search query
            user_id: User ID
            limit: Maximum results

        Returns:
            List of matching ChatSession instances
        """
        return await self.session_repo.search_by_title(query, user_id, limit)

    async def get_session_stats(
        self,
        user_id: int
    ) -> Dict[str, int]:
        """
        Get chat statistics for a user.

        Args:
            user_id: User ID

        Returns:
            Dictionary with chat statistics
        """
        total_sessions = await self.session_repo.count_by_user(user_id)

        # Get recent sessions
        recent_sessions = await self.session_repo.get_recent_sessions(
            user_id,
            days=30,
            limit=100
        )

        # Count total messages in recent sessions
        total_messages = 0
        for session in recent_sessions:
            msg_count = await self.message_repo.count_by_session(session.id)
            total_messages += msg_count

        return {
            "total_sessions": total_sessions,
            "recent_sessions_30d": len(recent_sessions),
            "total_messages_30d": total_messages
        }

    async def get_model_for_session(
        self,
        session_id: int
    ) -> Optional[str]:
        """
        Get the AI model name for a chat session.

        Args:
            session_id: Chat session ID

        Returns:
            Model name or None if not found
        """
        session = await self.session_repo.get_by_id(session_id)
        if not session:
            return None
        return session.model_name

    async def change_session_model(
        self,
        session_id: int,
        user_id: int,
        new_model: str
    ) -> Optional[ChatSession]:
        """
        Change the AI model for a chat session.

        Args:
            session_id: Chat session ID
            user_id: User ID (for ownership verification)
            new_model: New model name

        Returns:
            Updated ChatSession instance or None if not found/no access
        """
        # Verify session ownership
        session = await self.session_repo.get_by_id(session_id)
        if not session or session.user_id != user_id:
            return None

        return await self.session_repo.update(session_id, model_name=new_model)

    async def get_message(
        self,
        message_id: int,
        user_id: int
    ) -> Optional[ChatMessage]:
        """
        Get a message with access verification.

        Args:
            message_id: Message ID
            user_id: User ID (for access verification via session)

        Returns:
            ChatMessage instance or None if not found/no access
        """
        message = await self.message_repo.get_by_id(message_id)
        if not message:
            return None

        # Verify session ownership
        session = await self.session_repo.get_by_id(message.session_id)
        if not session or session.user_id != user_id:
            return None

        return message

    async def delete_message(
        self,
        message_id: int,
        user_id: int
    ) -> bool:
        """
        Delete a message with access verification.

        Args:
            message_id: Message ID
            user_id: User ID (for access verification via session)

        Returns:
            True if deleted, False if not found/no access
        """
        message = await self.message_repo.get_by_id(message_id)
        if not message:
            return False

        # Verify session ownership
        session = await self.session_repo.get_by_id(message.session_id)
        if not session or session.user_id != user_id:
            return False

        await self.message_repo.delete(message_id)
        return True

    async def get_user_model_config(
        self,
        user_id: int,
        config_type: str = "chat"
    ) -> Optional[Dict]:
        """
        Get user's model configuration for a specific type.

        Args:
            user_id: User ID
            config_type: Config type (chat, writer, embedding, image)

        Returns:
            Dictionary with model config or None
        """
        if not self.model_config_repo:
            return None

        config = await self.model_config_repo.get_by_user_and_type(user_id, config_type)
        if not config:
            return None

        return {
            "provider": config.provider,
            "model_name": config.model_name,
            "parameters": config.parameters or {}
        }

    async def create_automatic_title(
        self,
        session_id: int,
        user_id: int
    ) -> Optional[str]:
        """
        Generate an automatic title for a chat session based on first message.

        Args:
            session_id: Chat session ID
            user_id: User ID (for access verification)

        Returns:
            Generated title or None if no messages/no access
        """
        # Verify session ownership
        session = await self.session_repo.get_by_id(session_id)
        if not session or session.user_id != user_id:
            return None

        # Get first user message
        first_message = await self.message_repo.get_last_message(session_id, "user")
        if not first_message:
            return None

        # Generate title from first message content
        content = first_message.content
        if len(content) <= 50:
            title = content
        else:
            title = content[:47] + "..."

        # Update session title
        await self.session_repo.update_title(session_id, title)

        return title

    async def clone_session(
        self,
        session_id: int,
        user_id: int
    ) -> Optional[ChatSession]:
        """
        Clone a chat session (creates new session without messages).

        Args:
            session_id: Original session ID
            user_id: User ID (for ownership verification)

        Returns:
            New ChatSession instance or None if not found/no access
        """
        # Verify session ownership
        session = await self.session_repo.get_by_id(session_id)
        if not session or session.user_id != user_id:
            return None

        # Create new session with same settings
        new_session = await self.session_repo.create(
            user_id=user_id,
            title=f"{session.title} (Copy)",
            model_name=session.model_name,
            system_prompt=session.system_prompt
        )

        return new_session

    async def export_session(
        self,
        session_id: int,
        user_id: int
    ) -> Optional[Dict]:
        """
        Export a chat session with all messages.

        Args:
            session_id: Chat session ID
            user_id: User ID (for access verification)

        Returns:
            Dictionary with exported session data or None if no access
        """
        session_data = await self.get_session_with_messages(session_id, user_id)
        if not session_data:
            return None

        return {
            "title": session_data["title"],
            "model": session_data["model_name"],
            "created_at": session_data["created_at"].isoformat(),
            "messages": [
                {
                    "role": msg["role"],
                    "content": msg["content"],
                    "timestamp": msg["created_at"].isoformat()
                }
                for msg in session_data["messages"]
            ]
        }
