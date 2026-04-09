"""Batch generation ORM models for Sprint 7."""
from sqlalchemy import String, Text, Boolean, ForeignKey, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from typing import Optional
from uuid import UUID as UUID_TYPE, uuid4
from datetime import datetime, timezone
from backend.api.db.base import Base


class BatchJob(Base):
    """Batch generation job model."""
    __tablename__ = 'batch_jobs'

    id: Mapped[UUID_TYPE] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True
    )
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )

    # Job configuration
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    topics: Mapped[list] = mapped_column(JSONB, nullable=False)  # ["topic1", "topic2", ...]
    platform: Mapped[str] = mapped_column(String(50), nullable=False)  # wechat/zhihu/xiaohongshu
    # Style ID stored as string (no FK constraint - user_styles table may not exist yet)
    style_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    # Status tracking
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default='pending'  # pending/running/completed/failed/partial
    )
    total_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Configuration options
    concurrency: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    generate_images: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Results
    zip_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="batch_jobs")
    tasks: Mapped[list["BatchTask"]] = relationship(
        "BatchTask",
        back_populates="job",
        cascade="all, delete-orphan"
    )


class BatchTask(Base):
    """Batch generation sub-task model."""
    __tablename__ = 'batch_tasks'

    id: Mapped[UUID_TYPE] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True
    )
    job_id: Mapped[UUID_TYPE] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('batch_jobs.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )

    # Task content
    topic: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default='pending'  # pending/running/completed/failed
    )

    # Results
    article_id: Mapped[Optional[UUID_TYPE]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('articles.id'),
        nullable=True
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    job: Mapped["BatchJob"] = relationship("BatchJob", back_populates="tasks")
    article: Mapped[Optional["Article"]] = relationship("Article")
