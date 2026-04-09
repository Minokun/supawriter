"""Chat session and message ORM models."""
from sqlalchemy import String, Text, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional, List
from backend.api.db.base import Base, BaseModel


class ChatSession(Base, BaseModel):
    """AI chat session for multi-turn conversations."""
    __tablename__ = 'chat_sessions'

    user_id: Mapped[int] = mapped_column(
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    title: Mapped[str] = mapped_column(String(500), default="New Chat")
    model_name: Mapped[str] = mapped_column(String(100), default="gpt-4o")
    system_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationship
    messages: Mapped[List["ChatMessage"]] = relationship(
        "ChatMessage",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ChatMessage.created_at"
    )


class ChatMessage(Base, BaseModel):
    """Individual message in a chat session."""
    __tablename__ = 'chat_messages'

    session_id: Mapped[int] = mapped_column(
        ForeignKey('chat_sessions.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # user, assistant, system
    content: Mapped[str] = mapped_column(Text, nullable=False)
    thinking: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # AI thinking process

    # Relationship
    session: Mapped["ChatSession"] = relationship("ChatSession", back_populates="messages")
