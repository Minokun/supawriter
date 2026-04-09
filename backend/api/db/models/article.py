"""Article ORM model."""
from sqlalchemy import String, Text, Integer, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from typing import Optional
from uuid import UUID as UUID_TYPE, uuid4
from datetime import datetime, timezone
from backend.api.db.base import Base


class Article(Base):
    """Article model with full-text search and image configuration."""
    __tablename__ = 'articles'

    id: Mapped[UUID_TYPE] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="draft")  # draft, generating, completed, failed
    word_count: Mapped[int] = mapped_column(Integer, default=0)
    tags: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    article_metadata: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)  # Source, keywords, etc.
    image_config: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)  # Image insertion settings
    search_vector: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # For full-text search

    # Relationship
    author: Mapped["User"] = relationship("User", back_populates="articles")

    @property
    def is_completed(self) -> bool:
        """Check if article is completed."""
        return self.status == 'completed'
