#!/usr/bin/env python3
"""Check production database schema drift against expected runtime requirements."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Iterable

import psycopg2
from alembic.config import Config
from alembic.script import ScriptDirectory

from backend.api.db.base import Base
import backend.api.db.models  # noqa: F401


ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_INI = ROOT / "backend" / "api" / "db" / "migrations" / "alembic.ini"


REQUIRED_TABLES = set(Base.metadata.tables.keys()) | {
    "hotspot_sources",
    "hotspot_items",
    "hotspot_rank_history",
    "global_llm_providers",
    "tier_default_models",
    "llm_provider_templates",
    "user_model_configs",
    "alembic_version",
}

REQUIRED_COLUMNS = {
    "users": {"avatar_source", "membership_tier", "phone", "phone_verified", "email_verified"},
    "user_model_configs": {
        "chat_model",
        "writer_model",
        "embedding_model",
        "image_model",
        "default_temperature",
        "default_max_tokens",
        "default_top_p",
        "enable_streaming",
        "enable_thinking_process",
    },
    "hotspot_sources": {"id", "name", "enabled", "sort_order", "category"},
}


def fail(message: str) -> None:
    print(f"[FAIL] {message}")


def ok(message: str) -> None:
    print(f"[ OK ] {message}")


def get_database_url() -> str:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is required")
    return database_url


def get_expected_head() -> str:
    config = Config(str(ALEMBIC_INI))
    config.set_main_option("script_location", str(ROOT / "backend" / "api" / "db" / "migrations" / "alembic"))
    script = ScriptDirectory.from_config(config)
    head = script.get_current_head()
    if not head:
        raise RuntimeError("Unable to determine Alembic head revision")
    return head


def fetch_set(cursor, query: str, params: Iterable | None = None) -> set[str]:
    cursor.execute(query, tuple(params or ()))
    return {row[0] for row in cursor.fetchall()}


def main() -> int:
    database_url = get_database_url()
    expected_head = get_expected_head()
    has_failure = False

    conn = psycopg2.connect(database_url)
    try:
        with conn, conn.cursor() as cursor:
            cursor.execute("SELECT version_num FROM alembic_version")
            row = cursor.fetchone()
            if not row:
                fail("alembic_version table exists but has no revision row")
                has_failure = True
            else:
                current_version = row[0]
                if current_version == expected_head:
                    ok(f"Alembic revision matches head ({expected_head})")
                else:
                    fail(f"Alembic revision drift: current={current_version}, expected={expected_head}")
                    has_failure = True

            tables = fetch_set(
                cursor,
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                """,
            )
            missing_tables = sorted(REQUIRED_TABLES - tables)
            if missing_tables:
                fail(f"Missing required tables: {', '.join(missing_tables)}")
                has_failure = True
            else:
                ok("Required tables are present")

            for table_name, required_columns in REQUIRED_COLUMNS.items():
                columns = fetch_set(
                    cursor,
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = 'public' AND table_name = %s
                    """,
                    (table_name,),
                )
                missing_columns = sorted(required_columns - columns)
                if missing_columns:
                    fail(f"{table_name} is missing columns: {', '.join(missing_columns)}")
                    has_failure = True
                else:
                    ok(f"{table_name} required columns are present")
    finally:
        conn.close()

    return 1 if has_failure else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"[FAIL] schema drift check crashed: {exc}")
        raise SystemExit(1)
