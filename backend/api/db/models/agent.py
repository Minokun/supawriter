"""Writing Agent ORM models for Sprint 7."""
from sqlalchemy import String, Text, Boolean, ForeignKey, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from typing import Optional
from uuid import UUID as UUID_TYPE, uuid4
from datetime import datetime, timezone
from backend.api.db.base import Base


class WritingAgent(Base):
    """Writing Agent configuration model."""
    __tablename__ = 'writing_agents'

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

    # Basic configuration
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Trigger rules (JSON configuration)
    # Example: {"sources": ["baidu", "weibo"], "keywords": ["AI"], "min_heat": 100000}
    trigger_rules: Mapped[dict] = mapped_column(JSONB, nullable=False)

    # Generation configuration
    platform: Mapped[str] = mapped_column(String(50), nullable=False)  # Default output platform
    # Style ID stored as string (no FK constraint - user_styles table may not exist yet)
    style_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    generate_images: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Limit configuration
    max_daily: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    min_hot_score: Mapped[int] = mapped_column(Integer, default=70, nullable=False)

    # Statistics
    total_triggered: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    today_triggered: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_triggered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="writing_agents")
    drafts: Mapped[list["AgentDraft"]] = relationship(
        "AgentDraft",
        back_populates="agent",
        cascade="all, delete-orphan"
    )


class AgentDraft(Base):
    """Agent generated draft model."""
    __tablename__ = 'agent_drafts'

    id: Mapped[UUID_TYPE] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True
    )
    agent_id: Mapped[UUID_TYPE] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('writing_agents.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )

    # Source information
    hotspot_title: Mapped[str] = mapped_column(String(500), nullable=False)
    hotspot_source: Mapped[str] = mapped_column(String(50), nullable=False)
    hotspot_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    hotspot_heat: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Generated article
    article_id: Mapped[Optional[UUID_TYPE]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('articles.id'),
        nullable=True
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default='pending'  # pending/generating/completed/reviewed/discarded
    )

    # User actions
    user_rating: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 1-5 star rating
    user_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    agent: Mapped["WritingAgent"] = relationship("WritingAgent", back_populates="drafts")
    user: Mapped["User"] = relationship("User", back_populates="agent_drafts")
    article: Mapped[Optional["Article"]] = relationship("Article")
