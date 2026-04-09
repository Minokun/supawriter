#!/usr/bin/env python3
"""Repair schema drift before Alembic or runtime initialization."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import psycopg2
from psycopg2.extras import RealDictCursor
from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import ProgrammingError

# Make repository root importable even when this script is executed by file path.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.api.db.base import Base
import backend.api.db.models  # noqa: F401


def get_database_url() -> str:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is required")
    return database_url


def log(message: str) -> None:
    print(f"[repair] {message}")


def ensure_users_columns(cursor) -> None:
    cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS avatar_source VARCHAR(20)")
    cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS phone VARCHAR(20)")
    cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS phone_verified BOOLEAN DEFAULT FALSE")
    cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified BOOLEAN DEFAULT FALSE")
    cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS membership_tier VARCHAR(20) DEFAULT 'free'")
    cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_superuser BOOLEAN DEFAULT FALSE")
    cursor.execute("ALTER TABLE users DROP CONSTRAINT IF EXISTS check_membership_tier")
    cursor.execute(
        """
        ALTER TABLE users
        ADD CONSTRAINT check_membership_tier
        CHECK (membership_tier IN ('free', 'pro', 'ultra', 'superuser'))
        """
    )
    log("ensured users compatibility columns")


def ensure_user_topics_table(cursor) -> None:
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS user_topics (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            topic_name VARCHAR(200) NOT NULL,
            description TEXT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    cursor.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'user_topics_user_id_topic_name_key'
            ) THEN
                ALTER TABLE user_topics
                ADD CONSTRAINT user_topics_user_id_topic_name_key UNIQUE (user_id, topic_name);
            END IF;
        END $$;
        """
    )
    cursor.execute("CREATE INDEX IF NOT EXISTS ix_user_topics_id ON user_topics (id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS ix_user_topics_user_id ON user_topics (user_id)")
    log("ensured user_topics table and indexes")


def ensure_hotspot_tables(cursor) -> None:
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS hotspot_sources (
            id VARCHAR(50) PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            icon VARCHAR(10),
            enabled BOOLEAN NOT NULL DEFAULT TRUE,
            sort_order INTEGER NOT NULL DEFAULT 0,
            category VARCHAR(50)
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS hotspot_items (
            id SERIAL PRIMARY KEY,
            title VARCHAR(500) NOT NULL,
            url VARCHAR(1000),
            source VARCHAR(50) NOT NULL REFERENCES hotspot_sources(id),
            source_id VARCHAR(200),
            rank INTEGER NOT NULL,
            rank_prev INTEGER,
            rank_change INTEGER NOT NULL DEFAULT 0,
            hot_value INTEGER,
            hot_value_prev INTEGER,
            is_new BOOLEAN NOT NULL DEFAULT FALSE,
            description TEXT,
            icon_url VARCHAR(500),
            mobile_url VARCHAR(1000),
            published_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_hotspot_title_source UNIQUE (title, source)
        )
        """
    )
    cursor.execute("CREATE INDEX IF NOT EXISTS ix_hotspot_items_source ON hotspot_items (source)")
    cursor.execute("CREATE INDEX IF NOT EXISTS ix_hotspot_items_source_rank ON hotspot_items (source, rank)")
    cursor.execute("CREATE INDEX IF NOT EXISTS ix_hotspot_items_title ON hotspot_items (title)")

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS hotspot_rank_history (
            id SERIAL PRIMARY KEY,
            hotspot_item_id INTEGER NOT NULL REFERENCES hotspot_items(id) ON DELETE CASCADE,
            source VARCHAR(50) NOT NULL,
            rank INTEGER NOT NULL,
            hot_value INTEGER,
            is_new BOOLEAN NOT NULL DEFAULT FALSE,
            recorded_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS ix_hotspot_rank_history_hotspot_item_id ON hotspot_rank_history (hotspot_item_id)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS ix_hotspot_rank_history_recorded_at ON hotspot_rank_history (recorded_at)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS ix_rank_history_item_time ON hotspot_rank_history (hotspot_item_id, recorded_at)"
    )
    log("ensured hotspot tables and indexes")


def ensure_articles_schema(cursor) -> None:
    cursor.execute("ALTER TABLE articles ADD COLUMN IF NOT EXISTS username VARCHAR(100)")
    cursor.execute("ALTER TABLE articles ADD COLUMN IF NOT EXISTS topic VARCHAR(500)")
    cursor.execute("ALTER TABLE articles ADD COLUMN IF NOT EXISTS article_content TEXT")
    cursor.execute("ALTER TABLE articles ADD COLUMN IF NOT EXISTS summary TEXT")
    cursor.execute("ALTER TABLE articles ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}'::jsonb")
    cursor.execute("ALTER TABLE articles ADD COLUMN IF NOT EXISTS model_type VARCHAR(50)")
    cursor.execute("ALTER TABLE articles ADD COLUMN IF NOT EXISTS model_name VARCHAR(100)")
    cursor.execute("ALTER TABLE articles ADD COLUMN IF NOT EXISTS write_type VARCHAR(50)")
    cursor.execute("ALTER TABLE articles ADD COLUMN IF NOT EXISTS spider_num INTEGER")
    cursor.execute("ALTER TABLE articles ADD COLUMN IF NOT EXISTS custom_style TEXT")
    cursor.execute("ALTER TABLE articles ADD COLUMN IF NOT EXISTS is_transformed BOOLEAN DEFAULT FALSE")
    cursor.execute("ALTER TABLE articles ADD COLUMN IF NOT EXISTS original_article_id UUID")
    cursor.execute("ALTER TABLE articles ADD COLUMN IF NOT EXISTS image_task_id VARCHAR(100)")
    cursor.execute("ALTER TABLE articles ADD COLUMN IF NOT EXISTS image_enabled BOOLEAN DEFAULT FALSE")
    cursor.execute("ALTER TABLE articles ADD COLUMN IF NOT EXISTS image_similarity_threshold NUMERIC(3, 2)")
    cursor.execute("ALTER TABLE articles ADD COLUMN IF NOT EXISTS image_max_count INTEGER")
    cursor.execute("ALTER TABLE articles ADD COLUMN IF NOT EXISTS article_topic TEXT")
    cursor.execute("ALTER TABLE articles ADD COLUMN IF NOT EXISTS outline JSONB")
    cursor.execute("ALTER TABLE articles ADD COLUMN IF NOT EXISTS completed_at TIMESTAMPTZ")
    cursor.execute("ALTER TABLE articles ADD COLUMN IF NOT EXISTS title VARCHAR(500)")
    cursor.execute("ALTER TABLE articles ADD COLUMN IF NOT EXISTS content TEXT")
    cursor.execute("ALTER TABLE articles ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'draft'")

    cursor.execute(
        """
        UPDATE articles a
        SET username = u.username
        FROM users u
        WHERE a.user_id = u.id AND (a.username IS NULL OR a.username = '')
        """
    )
    cursor.execute("UPDATE articles SET topic = COALESCE(topic, title, '未命名主题')")
    cursor.execute("UPDATE articles SET title = COALESCE(title, topic, '未命名文章')")
    cursor.execute("UPDATE articles SET content = COALESCE(content, article_content)")
    cursor.execute("UPDATE articles SET article_content = COALESCE(article_content, content)")
    cursor.execute("UPDATE articles SET metadata = COALESCE(metadata, '{}'::jsonb)")
    cursor.execute("UPDATE articles SET status = COALESCE(status, 'draft')")
    cursor.execute("UPDATE articles SET image_enabled = COALESCE(image_enabled, FALSE)")
    cursor.execute("UPDATE articles SET is_transformed = COALESCE(is_transformed, FALSE)")

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_articles_username ON articles(username)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_articles_user_id ON articles(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_articles_topic ON articles(topic)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_articles_title ON articles(title)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_articles_status ON articles(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_articles_model_type ON articles(model_type)")

    cursor.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'articles_original_article_id_fkey'
            ) THEN
                ALTER TABLE articles
                ADD CONSTRAINT articles_original_article_id_fkey
                FOREIGN KEY (original_article_id) REFERENCES articles(id);
            END IF;
        END $$;
        """
    )
    log("ensured articles compatibility columns and indexes")


def ensure_missing_orm_tables(database_url: str) -> None:
    engine = create_engine(database_url)
    try:
        inspector = inspect(engine)
        created_tables: list[str] = []
        managed_by_sql = {"hotspot_sources", "hotspot_items", "hotspot_rank_history"}

        for table in Base.metadata.sorted_tables:
            if table.name in managed_by_sql:
                continue

            if inspector.has_table(table.name):
                continue

            try:
                table.create(bind=engine, checkfirst=True)
            except ProgrammingError as exc:
                if "already exists" in str(exc).lower():
                    log(f"skipped existing ORM object while creating table {table.name}: {exc.__class__.__name__}")
                    continue
                raise
            created_tables.append(table.name)

        if created_tables:
            log(f"created missing ORM tables: {', '.join(created_tables)}")
        else:
            log("all ORM-managed tables already exist")
    finally:
        engine.dispose()


def main() -> int:
    database_url = get_database_url()
    conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
    try:
        with conn:
            with conn.cursor() as cursor:
                ensure_users_columns(cursor)
                ensure_user_topics_table(cursor)
                ensure_hotspot_tables(cursor)
                ensure_articles_schema(cursor)
        ensure_missing_orm_tables(database_url)
        log("schema drift repair complete")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
