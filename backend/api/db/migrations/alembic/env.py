"""Alembic environment configuration for async migrations."""
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context
import asyncio
import os

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import all models
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
from backend.api.db.base import Base
from backend.api.db.models import (
    User, OAuthAccount, Article,
    ChatSession, ChatMessage,
    UserApiKey, UserModelConfig, UserPreferences,
    LLMProvider, UserServiceConfig,
    UserQuota, QuotaUsage,
    AuditLog,
    SystemSetting,
    AlertKeyword, AlertRecord, UserStats,
    BatchJob, BatchTask,
    WritingAgent, AgentDraft,
)

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Add your model's MetaData object here for 'autogenerate' support
target_metadata = Base.metadata

# Get database URL from environment
database_url = os.getenv('DATABASE_URL', 'postgresql://supawriter:password@localhost:5432/supawriter')
async_url = database_url.replace('postgresql://', 'postgresql+asyncpg://')
config.set_main_option('sqlalchemy.url', async_url)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in async mode."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
