"""System settings ORM model."""
from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional
from backend.api.db.base import Base, BaseModel


class SystemSetting(Base, BaseModel):
    """Global system configuration settings."""
    __tablename__ = 'system_settings'

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
