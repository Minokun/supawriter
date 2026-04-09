# -*- coding: utf-8 -*-
"""Article service with content management and business logic."""
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Dict, List
from datetime import datetime
from backend.api.db.models.article import Article
from backend.api.repositories.article import ArticleRepository
from backend.api.repositories.quota import QuotaRepository


class ArticleService:
    """
    Service layer for article operations.

    Handles business logic for article creation, publishing,
    status management, SEO optimization, and interaction tracking.
    """

    def __init__(
        self,
        session: AsyncSession,
        article_repository: ArticleRepository,
        quota_repository: Optional[QuotaRepository] = None
    ):
        """
        Initialize ArticleService.

        Args:
            session: Database session
            article_repository: Article repository instance
            quota_repository: Optional quota repository for quota checks
        """
        self.session = session
        self.article_repo = article_repository
        self.quota_repo = quota_repository

    async def create_article(
        self,
        user_id: int,
        title: str,
        content: str = "",
        slug: Optional[str] = None,
        cover_image: Optional[str] = None,
        tags: Optional[List[str]] = None,
        status: str = "draft",
        check_quota: bool = True
    ) -> Optional[Article]:
        """
        Create a new article with optional quota check.

        Args:
            user_id: User ID
            title: Article title
            content: Article content
            slug: Optional URL slug
            cover_image: Optional cover image URL
            tags: Optional tags list
            status: Article status (draft, published, archived)
            check_quota: Whether to check quota before creating

        Returns:
            Created Article instance or None if quota check fails
        """
        # Check quota if required
        if check_quota and self.quota_repo:
            from backend.api.services.quota import QuotaService
            quota_service = QuotaService(self.session, self.quota_repo)
            # Check if user can create more articles
            has_quota = await quota_service.check_quota(
                user_id=user_id,
                quota_type="article_count"
            )
            if not has_quota:
                return None

        # Generate slug if not provided
        if not slug:
            slug = await self._generate_slug(title)

        # Create article
        article = await self.article_repo.create(
            user_id=user_id,
            title=title,
            slug=slug,
            content=content,
            cover_image=cover_image,
            tags=tags or [],
            status=status
        )

        # Consume quota if applicable
        if check_quota and self.quota_repo and article:
            from backend.api.services.quota import QuotaService
            quota_service = QuotaService(self.session, self.quota_repo)
            await quota_service.consume_quota(
                user_id=user_id,
                quota_type="article_count",
                amount=1
            )

        return article

    async def update_article(
        self,
        article_id: int,
        user_id: int,
        title: Optional[str] = None,
        content: Optional[str] = None,
        cover_image: Optional[str] = None,
        tags: Optional[List[str]] = None,
        seo_title: Optional[str] = None,
        seo_desc: Optional[str] = None,
        seo_keywords: Optional[str] = None
    ) -> Optional[Article]:
        """
        Update article with validation and ownership check.

        Args:
            article_id: Article ID
            user_id: User ID (for ownership verification)
            title: Optional new title
            content: Optional new content
            cover_image: Optional new cover image
            tags: Optional new tags
            seo_title: Optional SEO title
            seo_desc: Optional SEO description
            seo_keywords: Optional SEO keywords

        Returns:
            Updated Article instance or None if not found/not owned
        """
        # Get article
        article = await self.article_repo.get_by_id(article_id)
        if not article or article.user_id != user_id:
            return None

        # Prepare update data
        update_data = {}
        if title is not None:
            update_data["title"] = title
        if content is not None:
            update_data["content"] = content
        if cover_image is not None:
            update_data["cover_image"] = cover_image
        if tags is not None:
            update_data["tags"] = tags
        if seo_title is not None:
            update_data["seo_title"] = seo_title
        if seo_desc is not None:
            update_data["seo_desc"] = seo_desc
        if seo_keywords is not None:
            update_data["seo_keywords"] = seo_keywords

        # Update article
        if update_data:
            article = await self.article_repo.update(article_id, **update_data)

        return article

    async def publish_article(
        self,
        article_id: int,
        user_id: int
    ) -> Optional[Article]:
        """
        Publish an article with validation.

        Args:
            article_id: Article ID
            user_id: User ID (for ownership verification)

        Returns:
            Published Article instance or None if not found/not owned
        """
        # Get article
        article = await self.article_repo.get_by_id(article_id)
        if not article or article.user_id != user_id:
            return None

        # Validate article has content
        if not article.content or len(article.content.strip()) < 10:
            return None

        # Update status and published_at
        article = await self.article_repo.update(
            article_id,
            status="published",
            published_at=datetime.utcnow()
        )

        return article

    async def unpublish_article(
        self,
        article_id: int,
        user_id: int
    ) -> Optional[Article]:
        """
        Unpublish an article (revert to draft).

        Args:
            article_id: Article ID
            user_id: User ID (for ownership verification)

        Returns:
            Updated Article instance or None if not found/not owned
        """
        # Get article
        article = await self.article_repo.get_by_id(article_id)
        if not article or article.user_id != user_id:
            return None

        # Update status
        return await self.article_repo.update(article_id, status="draft")

    async def delete_article(
        self,
        article_id: int,
        user_id: int
    ) -> bool:
        """
        Delete an article with ownership verification.

        Args:
            article_id: Article ID
            user_id: User ID (for ownership verification)

        Returns:
            True if deleted, False if not found/not owned
        """
        # Get article
        article = await self.article_repo.get_by_id(article_id)
        if not article or article.user_id != user_id:
            return False

        # Delete article
        await self.article_repo.delete(article_id)
        return True

    async def get_user_articles(
        self,
        user_id: int,
        status: Optional[str] = None,
        offset: int = 0,
        limit: int = 20
    ) -> List[Article]:
        """
        Get articles for a user with optional status filter.

        Args:
            user_id: User ID
            status: Optional status filter
            offset: Pagination offset
            limit: Pagination limit

        Returns:
            List of Article instances
        """
        return await self.article_repo.get_by_user_id(
            user_id=user_id,
            offset=offset,
            limit=limit,
            status=status
        )

    async def get_article_with_access_check(
        self,
        article_id: int,
        user_id: int
    ) -> Optional[Article]:
        """
        Get article with access verification.

        Args:
            article_id: Article ID
            user_id: User ID

        Returns:
            Article instance or None if not found/no access
        """
        article = await self.article_repo.get_by_id(article_id)
        if not article or article.user_id != user_id:
            return None
        return article

    async def search_articles(
        self,
        query: str,
        user_id: int,
        limit: int = 20
    ) -> List[Article]:
        """
        Search articles by title and content.

        Args:
            query: Search query
            user_id: User ID
            limit: Maximum results

        Returns:
            List of matching Article instances
        """
        # Search by title
        title_results = await self.article_repo.search_by_title(
            query=query,
            user_id=user_id,
            limit=limit
        )

        # Search by content
        content_results = await self.article_repo.search_by_content(
            query=query,
            user_id=user_id,
            limit=limit
        )

        # Merge and deduplicate (prioritize title matches)
        seen_ids = set()
        results = []

        for article in title_results:
            if article.id not in seen_ids:
                results.append(article)
                seen_ids.add(article.id)

        for article in content_results:
            if article.id not in seen_ids:
                results.append(article)
                seen_ids.add(article.id)

        return results[:limit]

    async def update_seo_metadata(
        self,
        article_id: int,
        user_id: int,
        seo_title: Optional[str] = None,
        seo_desc: Optional[str] = None,
        seo_keywords: Optional[str] = None
    ) -> Optional[Article]:
        """
        Update SEO metadata for an article.

        Args:
            article_id: Article ID
            user_id: User ID (for ownership verification)
            seo_title: SEO title
            seo_desc: SEO description
            seo_keywords: SEO keywords

        Returns:
            Updated Article instance or None if not found/not owned
        """
        # Get article
        article = await self.article_repo.get_by_id(article_id)
        if not article or article.user_id != user_id:
            return None

        # Generate SEO metadata if not provided
        if not seo_title:
            seo_title = await self._generate_seo_title(article.title)
        if not seo_desc:
            seo_desc = await self._generate_seo_desc(article.content)
        if not seo_keywords:
            seo_keywords = await self._generate_seo_keywords(article.tags, article.title)

        # Update metadata
        return await self.article_repo.update(
            article_id,
            seo_title=seo_title,
            seo_desc=seo_desc,
            seo_keywords=seo_keywords
        )

    async def increment_view_count(
        self,
        article_id: int
    ) -> bool:
        """
        Increment article view count.

        Args:
            article_id: Article ID

        Returns:
            True if incremented, False if not found
        """
        article = await self.article_repo.get_by_id(article_id)
        if not article:
            return False

        new_count = (article.view_count or 0) + 1
        await self.article_repo.update(article_id, view_count=new_count)
        return True

    async def get_article_stats(
        self,
        user_id: int
    ) -> Dict[str, int]:
        """
        Get article statistics for a user.

        Args:
            user_id: User ID

        Returns:
            Dictionary with article counts by status
        """
        total = await self.article_repo.count_by_user(user_id)
        published = await self.article_repo.count_by_user(user_id, "published")
        draft = await self.article_repo.count_by_user(user_id, "draft")
        archived = await self.article_repo.count_by_user(user_id, "archived")

        return {
            "total": total,
            "published": published,
            "draft": draft,
            "archived": archived
        }

    async def bulk_update_status(
        self,
        article_ids: List[int],
        user_id: int,
        new_status: str
    ) -> int:
        """
        Bulk update article status with ownership verification.

        Args:
            article_ids: List of article IDs
            user_id: User ID (for ownership verification)
            new_status: New status to set

        Returns:
            Number of articles updated
        """
        # Verify ownership for all articles
        valid_ids = []
        for aid in article_ids:
            article = await self.article_repo.get_by_id(aid)
            if article and article.user_id == user_id:
                valid_ids.append(aid)

        if not valid_ids:
            return 0

        return await self.article_repo.bulk_update_status(valid_ids, new_status)

    async def _generate_slug(self, title: str) -> str:
        """
        Generate a URL slug from title.

        Args:
            title: Article title

        Returns:
            Generated slug
        """
        import re
        from uuid import uuid4

        # Remove special characters and convert to lowercase
        slug = re.sub(r'[^\w\s-]', '', title.lower())
        slug = re.sub(r'[-\s]+', '-', slug)
        slug = slug.strip('-')

        # Add unique suffix
        unique_suffix = uuid4().hex[:8]
        return f"{slug}-{unique_suffix}"

    async def _generate_seo_title(self, title: str) -> str:
        """
        Generate SEO title from article title.

        Args:
            title: Article title

        Returns:
            Generated SEO title
        """
        # Use original title if under 60 chars
        if len(title) <= 60:
            return title

        # Truncate and add ellipsis
        return title[:57] + "..."

    async def _generate_seo_desc(self, content: str) -> str:
        """
        Generate SEO description from content.

        Args:
            content: Article content

        Returns:
            Generated SEO description
        """
        import re

        # Remove HTML tags and extra whitespace
        clean_content = re.sub(r'<[^>]+>', ' ', content)
        clean_content = re.sub(r'\s+', ' ', clean_content).strip()

        # Truncate to 160 chars
        if len(clean_content) <= 160:
            return clean_content

        return clean_content[:157] + "..."

    async def _generate_seo_keywords(
        self,
        tags: List[str],
        title: str
    ) -> str:
        """
        Generate SEO keywords from tags and title.

        Args:
            tags: Article tags
            title: Article title

        Returns:
            Generated SEO keywords string
        """
        import re

        # Extract words from title
        title_words = re.findall(r'\w+', title.lower())

        # Combine tags and title words
        all_keywords = []
        if tags:
            all_keywords.extend([tag.lower() for tag in tags])
        all_keywords.extend([w for w in title_words if len(w) > 3])

        # Deduplicate and join
        unique_keywords = list(dict.fromkeys(all_keywords))
        return ', '.join(unique_keywords[:10])
