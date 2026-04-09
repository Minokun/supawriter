"""Article repository with content management operations."""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, delete, func
from typing import Optional, List
from uuid import UUID
from backend.api.db.models.article import Article
from backend.api.repositories.base import BaseRepository


class ArticleRepository(BaseRepository[Article]):
    """
    Repository for Article model with content-specific operations.

    Extends BaseRepository with article-specific queries for content
    management, status tracking, and user article filtering.
    """

    def __init__(self, session: AsyncSession):
        """Initialize Article repository."""
        super().__init__(session, Article)

    async def get_by_user_id(
        self,
        user_id: int,
        offset: int = 0,
        limit: int = 100,
        status: Optional[str] = None
    ) -> List[Article]:
        """
        Get all articles for a specific user.

        Args:
            user_id: User ID
            offset: Number of records to skip
            limit: Maximum number of records to return
            status: Optional status filter

        Returns:
            List of Article instances
        """
        filters = {"user_id": user_id}
        if status:
            filters["status"] = status

        return await self.list(filters=filters, offset=offset, limit=limit, order_by="created_at DESC")

    async def get_by_status(
        self,
        status: str,
        offset: int = 0,
        limit: int = 100
    ) -> List[Article]:
        """
        Get articles by status.

        Args:
            status: Article status (draft, generating, completed, failed)
            offset: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of Article instances
        """
        return await self.list(
            filters={"status": status},
            offset=offset,
            limit=limit,
            order_by="created_at DESC"
        )

    async def get_by_user_and_status(
        self,
        user_id: int,
        status: str,
        offset: int = 0,
        limit: int = 100
    ) -> List[Article]:
        """
        Get articles for a user with a specific status.

        Args:
            user_id: User ID
            status: Article status
            offset: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of Article instances
        """
        return await self.list(
            filters={"user_id": user_id, "status": status},
            offset=offset,
            limit=limit,
            order_by="created_at DESC"
        )

    async def search_by_title(
        self,
        query: str,
        user_id: Optional[int] = None,
        limit: int = 20
    ) -> List[Article]:
        """
        Search articles by title (case-insensitive partial match).

        Args:
            query: Search query string
            user_id: Optional user ID to filter by
            limit: Maximum results to return

        Returns:
            List of matching Article instances
        """
        search_pattern = f"%{query}%"

        stmt = select(self.model).where(self.model.title.ilike(search_pattern))

        if user_id:
            stmt = stmt.where(self.model.user_id == user_id)

        stmt = stmt.order_by(self.model.created_at.desc()).limit(limit)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_status(self, article_id: UUID, status: str) -> Optional[Article]:
        """
        Update article status.

        Args:
            article_id: Article ID (UUID)
            status: New status (draft, generating, completed, failed)

        Returns:
            Updated Article instance or None if not found
        """
        return await self.update(article_id, status=status)

    async def update_word_count(self, article_id: UUID, word_count: int) -> Optional[Article]:
        """
        Update article word count.

        Args:
            article_id: Article ID (UUID)
            word_count: New word count

        Returns:
            Updated Article instance or None if not found
        """
        return await self.update(article_id, word_count=word_count)

    async def update_content(
        self,
        article_id: UUID,
        content: str
    ) -> Optional[Article]:
        """
        Update article content.

        Args:
            article_id: Article ID (UUID)
            content: New content

        Returns:
            Updated Article instance or None if not found
        """
        return await self.update(article_id, content=content)

    async def update_metadata(
        self,
        article_id: UUID,
        metadata: dict
    ) -> Optional[Article]:
        """
        Update article metadata.

        Args:
            article_id: Article ID (UUID)
            metadata: New metadata dictionary

        Returns:
            Updated Article instance or None if not found
        """
        return await self.update(article_id, article_metadata=metadata)

    async def update_image_config(
        self,
        article_id: UUID,
        image_config: dict
    ) -> Optional[Article]:
        """
        Update article image configuration.

        Args:
            article_id: Article ID (UUID)
            image_config: New image configuration dictionary

        Returns:
            Updated Article instance or None if not found
        """
        return await self.update(article_id, image_config=image_config)

    async def update_tags(
        self,
        article_id: UUID,
        tags: list
    ) -> Optional[Article]:
        """
        Update article tags.

        Args:
            article_id: Article ID (UUID)
            tags: New tags list

        Returns:
            Updated Article instance or None if not found
        """
        return await self.update(article_id, tags=tags)

    async def get_completed_articles(
        self,
        user_id: int,
        offset: int = 0,
        limit: int = 100
    ) -> List[Article]:
        """
        Get all completed articles for a user.

        Args:
            user_id: User ID
            offset: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of completed Article instances
        """
        return await self.get_by_user_and_status(user_id, "completed", offset, limit)

    async def get_draft_articles(
        self,
        user_id: int,
        offset: int = 0,
        limit: int = 100
    ) -> List[Article]:
        """
        Get all draft articles for a user.

        Args:
            user_id: User ID
            offset: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of draft Article instances
        """
        return await self.get_by_user_and_status(user_id, "draft", offset, limit)

    async def count_by_user(self, user_id: int, status: Optional[str] = None) -> int:
        """
        Count articles for a user.

        Args:
            user_id: User ID
            status: Optional status filter

        Returns:
            Number of articles
        """
        filters = {"user_id": user_id}
        if status:
            filters["status"] = status

        return await self.count(filters=filters)

    async def get_recent_articles(
        self,
        user_id: Optional[int] = None,
        limit: int = 10
    ) -> List[Article]:
        """
        Get recent articles.

        Args:
            user_id: Optional user ID to filter by
            limit: Maximum number of articles to return

        Returns:
            List of recent Article instances
        """
        if user_id:
            return await self.get_by_user_id(user_id, limit=limit)

        return await self.get_all(limit=limit, order_by="created_at DESC")

    async def delete_by_user(self, user_id: int) -> int:
        """
        Delete all articles for a user.

        Args:
            user_id: User ID

        Returns:
            Number of articles deleted
        """
        stmt = delete(self.model).where(self.model.user_id == user_id)
        result = await self.session.execute(stmt)
        return result.rowcount

    async def get_article_with_relationships(self, article_id: UUID) -> Optional[Article]:
        """
        Get article with author relationship pre-loaded.

        Args:
            article_id: Article ID (UUID)

        Returns:
            Article instance or None if not found
        """
        # For now, just get the article. In the future, we can use eager loading
        return await self.get_by_id(article_id)

    async def search_by_content(
        self,
        query: str,
        user_id: Optional[int] = None,
        limit: int = 20
    ) -> List[Article]:
        """
        Search articles by content (case-insensitive partial match).

        Args:
            query: Search query string
            user_id: Optional user ID to filter by
            limit: Maximum results to return

        Returns:
            List of matching Article instances
        """
        search_pattern = f"%{query}%"

        stmt = select(self.model).where(self.model.content.ilike(search_pattern))

        if user_id:
            stmt = stmt.where(self.model.user_id == user_id)

        stmt = stmt.order_by(self.model.created_at.desc()).limit(limit)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_articles_in_status_range(
        self,
        statuses: List[str],
        user_id: Optional[int] = None,
        offset: int = 0,
        limit: int = 100
    ) -> List[Article]:
        """
        Get articles with status in a specific range.

        Args:
            statuses: List of statuses to include
            user_id: Optional user ID to filter by
            offset: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of Article instances
        """
        stmt = select(self.model).where(self.model.status.in_(statuses))

        if user_id:
            stmt = stmt.where(self.model.user_id == user_id)

        stmt = stmt.order_by(self.model.created_at.desc()).offset(offset).limit(limit)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def bulk_update_status(
        self,
        article_ids: List[UUID],
        new_status: str
    ) -> int:
        """
        Bulk update status for multiple articles.

        Args:
            article_ids: List of article IDs (UUIDs)
            new_status: New status to set

        Returns:
            Number of articles updated
        """
        from sqlalchemy import update as sqlalchemy_update

        stmt = (
            sqlalchemy_update(self.model)
            .where(self.model.id.in_(article_ids))
            .values(status=new_status)
        )

        result = await self.session.execute(stmt)
        return result.rowcount
