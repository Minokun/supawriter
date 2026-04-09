"""User configuration ORM models."""
from sqlalchemy import String, Text, Integer, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB
from typing import Optional
from backend.api.db.base import Base, BaseModel


class UserApiKey(Base, BaseModel):
    """Encrypted API keys for third-party services."""
    __tablename__ = 'user_api_keys'

    user_id: Mapped[int] = mapped_column(
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    service_name: Mapped[str] = mapped_column(String(50), nullable=False)  # openai, anthropic, qiniu
    encrypted_key: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class UserModelConfig(Base, BaseModel):
    """AI model configurations for different purposes."""
    __tablename__ = 'user_model_configs'

    user_id: Mapped[int] = mapped_column(
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    config_type: Mapped[str] = mapped_column(String(50), nullable=False)  # chat, writer, embedding, image
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    parameters: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)  # temperature, max_tokens, etc.


class UserPreferences(Base, BaseModel):
    """User preference settings."""
    __tablename__ = 'user_preferences'

    user_id: Mapped[int] = mapped_column(
        ForeignKey('users.id', ondelete='CASCADE'),
        primary_key=True
    )
    editor_theme: Mapped[str] = mapped_column(String(20), default="light")
    editor_font_size: Mapped[int] = mapped_column(Integer, default=14)
    notification_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    wechat_preview_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    additional_settings: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)


class LLMProvider(Base, BaseModel):
    """User-level LLM provider configurations."""
    __tablename__ = 'llm_providers'

    user_id: Mapped[int] = mapped_column(
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    provider_name: Mapped[str] = mapped_column(String(50), nullable=False)
    api_endpoint: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    config: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)


class UserServiceConfig(Base, BaseModel):
    """Third-party service configurations."""
    __tablename__ = 'user_service_configs'

    user_id: Mapped[int] = mapped_column(
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    service_name: Mapped[str] = mapped_column(String(50), nullable=False)  # qiniu, serper
    config: Mapped[dict] = mapped_column(JSONB, nullable=False)
