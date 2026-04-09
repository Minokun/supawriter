"""User and OAuth account ORM models."""
from sqlalchemy import String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional, List
from datetime import datetime
from backend.api.db.base import Base, BaseModel


class User(Base, BaseModel):
    """User model supporting local accounts and OAuth."""
    __tablename__ = 'users'

    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    display_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    avatar_source: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # 'google', 'wechat', 'manual'
    motto: Mapped[str] = mapped_column(Text, default="创作改变世界")
    phone: Mapped[Optional[str]] = mapped_column(String(20), unique=True, nullable=True)
    phone_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
    membership_tier: Mapped[str] = mapped_column(String(20), default="free")

    # Relationships
    oauth_accounts: Mapped[List["OAuthAccount"]] = relationship(
        "OAuthAccount",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    articles: Mapped[List["Article"]] = relationship(
        "Article",
        back_populates="author",
        cascade="all, delete-orphan"
    )
    user_topics: Mapped[List["UserTopic"]] = relationship(
        "UserTopic",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    alert_keywords: Mapped[List["AlertKeyword"]] = relationship(
        "AlertKeyword",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    alert_records: Mapped[List["AlertRecord"]] = relationship(
        "AlertRecord",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    user_stats: Mapped[Optional["UserStats"]] = relationship(
        "UserStats",
        back_populates="user",
        uselist=False
    )
    batch_jobs: Mapped[List["BatchJob"]] = relationship(
        "BatchJob",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    writing_agents: Mapped[List["WritingAgent"]] = relationship(
        "WritingAgent",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    agent_drafts: Mapped[List["AgentDraft"]] = relationship(
        "AgentDraft",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    subscription: Mapped[Optional["Subscription"]] = relationship(
        "Subscription",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan"
    )


class OAuthAccount(Base, BaseModel):
    """OAuth account linkage for third-party authentication."""
    __tablename__ = 'oauth_accounts'

    user_id: Mapped[int] = mapped_column(
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False)  # google, wechat
    provider_user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    access_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    refresh_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    token_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationship
    user: Mapped["User"] = relationship("User", back_populates="oauth_accounts")


class UserTopic(Base, BaseModel):
    """User topic model for saved research topics."""
    __tablename__ = 'user_topics'

    user_id: Mapped[int] = mapped_column(
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    topic_name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationship
    user: Mapped["User"] = relationship("User", back_populates="user_topics")
