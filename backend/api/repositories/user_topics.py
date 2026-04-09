"""User Topics Repository - Data access layer for user_topics table."""
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from backend.api.db.models.user import UserTopic
from backend.api.repositories.base import BaseRepository


class UserTopicsRepository(BaseRepository[UserTopic]):
    """User topics data access layer extending BaseRepository."""

    def __init__(self, session: AsyncSession):
        """Initialize UserTopics repository."""
        super().__init__(session, UserTopic)

    async def get_user_topics(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all topics for a user."""
        stmt = select(UserTopic).where(
            UserTopic.user_id == user_id
        ).order_by(UserTopic.created_at.desc())

        result = await self.session.execute(stmt)
        topics = result.scalars().all()

        return [
            {
                "id": topic.id,
                "user_id": topic.user_id,
                "topic_name": topic.topic_name,
                "description": topic.description,
                "created_at": topic.created_at.isoformat() if topic.created_at else None,
                "updated_at": topic.updated_at.isoformat() if topic.updated_at else None,
            }
            for topic in topics
        ]

    async def create_user_topic(
        self,
        user_id: int,
        topic_name: str,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new topic for a user."""
        # Check if topic already exists
        existing_stmt = select(UserTopic).where(
            and_(
                UserTopic.user_id == user_id,
                UserTopic.topic_name == topic_name
            )
        )
        existing_result = await self.session.execute(existing_stmt)
        if existing_result.scalar_one_or_none():
            raise ValueError(f"主题 '{topic_name}' 已存在")

        # Create new topic
        new_topic = UserTopic(
            user_id=user_id,
            topic_name=topic_name,
            description=description
        )
        self.session.add(new_topic)
        await self.session.flush()
        await self.session.refresh(new_topic)

        return {
            "id": new_topic.id,
            "user_id": new_topic.user_id,
            "topic_name": new_topic.topic_name,
            "description": new_topic.description,
            "created_at": new_topic.created_at.isoformat() if new_topic.created_at else None,
            "updated_at": new_topic.updated_at.isoformat() if new_topic.updated_at else None,
        }

    async def delete_user_topic(self, user_id: int, topic_id: int) -> bool:
        """Delete a topic."""
        stmt = select(UserTopic).where(
            and_(
                UserTopic.id == topic_id,
                UserTopic.user_id == user_id
            )
        )
        result = await self.session.execute(stmt)
        topic = result.scalar_one_or_none()

        if not topic:
            return False

        await self.session.delete(topic)
        return True

    async def get_topic_by_id(self, user_id: int, topic_id: int) -> Optional[Dict[str, Any]]:
        """Get a topic by ID."""
        stmt = select(UserTopic).where(
            and_(
                UserTopic.id == topic_id,
                UserTopic.user_id == user_id
            )
        )
        result = await self.session.execute(stmt)
        topic = result.scalar_one_or_none()

        if not topic:
            return None

        return {
            "id": topic.id,
            "user_id": topic.user_id,
            "topic_name": topic.topic_name,
            "description": topic.description,
            "created_at": topic.created_at.isoformat() if topic.created_at else None,
            "updated_at": topic.updated_at.isoformat() if topic.updated_at else None,
        }
