"""Database base configuration - engines and Base class."""
from sqlalchemy import create_engine, Column, Integer, DateTime
from sqlalchemy.orm import DeclarativeBase, declared_attr, Mapped, mapped_column
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from sqlalchemy.pool import QueuePool
from datetime import datetime, timezone
import os
import logging

logger = logging.getLogger(__name__)


def get_database_url() -> str:
    """Get database URL from environment or construct from components."""
    database_url = os.getenv('DATABASE_URL')

    if not database_url:
        host = os.getenv('POSTGRES_HOST', 'localhost')
        port = os.getenv('POSTGRES_PORT', '5432')
        database = os.getenv('POSTGRES_DB', 'supawriter')
        user = os.getenv('POSTGRES_USER', 'supawriter')
        password = os.getenv('POSTGRES_PASSWORD', '')
        database_url = f"postgresql://{user}:{password}@{host}:{port}/{database}"

    return database_url


def create_db_engine():
    """Create synchronous database engine with connection pooling."""
    database_url = get_database_url()

    engine_obj = create_engine(
        database_url,
        poolclass=QueuePool,
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
        pool_recycle=3600,
        pool_pre_ping=True,
        echo=False,
        echo_pool=False,
    )
    logger.info("✓ Database engine created successfully")
    return engine_obj


def create_async_db_engine() -> AsyncEngine:
    """Create async database engine for FastAPI."""
    database_url = get_database_url()
    async_url = database_url.replace('postgresql://', 'postgresql+asyncpg://')

    engine_obj = create_async_engine(
        async_url,
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
        pool_recycle=3600,
        pool_pre_ping=True,
        echo=False,
    )
    logger.info("✓ Async database engine created successfully")
    return engine_obj


# Create global engine instances
engine = create_db_engine()
async_engine = create_async_db_engine()


class Base(DeclarativeBase):
    """Base class for all ORM models using SQLAlchemy 2.0 DeclarativeBase."""
    pass


class BaseModel:
    """Mixin class with common fields for all models."""

    @declared_attr.directive
    def __tablename__(cls) -> str:
        return cls.__name__.lower() + 's'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )
