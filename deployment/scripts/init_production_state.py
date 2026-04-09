#!/usr/bin/env python3
"""Idempotent production state initialization after migrations."""

from __future__ import annotations

import os
from datetime import datetime, timezone

import psycopg2
from psycopg2.extras import Json, RealDictCursor


SUPER_ADMIN_EMAILS = [
    email.strip()
    for email in os.getenv("SUPER_ADMIN_EMAILS", "").split(",")
    if email.strip()
]

DEFAULT_TIER_MODELS = {
    "free": ("deepseek:deepseek-chat", "deepseek:deepseek-chat", 5),
    "pro": ("deepseek:deepseek-chat", "deepseek:deepseek-chat", 50),
    "ultra": ("openai:gpt-4o", "openai:gpt-4o", 200),
}

DEFAULT_HOTSPOT_SOURCES = [
    ("ifeng", "凤凰网", True, 0, "新闻"),
    ("baidu", "百度热搜", True, 0, "综合"),
    ("tieba", "贴吧热搜", True, 1, "综合"),
    ("weibo", "微博热搜", True, 1, "综合"),
    ("douyin", "抖音热搜", True, 2, "短视频"),
    ("zhihu", "知乎热榜", True, 3, "综合"),
    ("bilibili", "B站热榜", True, 4, "短视频"),
    ("thepaper", "澎湃新闻", True, 5, "新闻"),
    ("36kr", "36氪", True, 6, "科技"),
    ("cls", "财联社", True, 7, "财经"),
    ("wallstreet", "华尔街见闻", True, 8, "财经"),
    ("toutiao", "今日头条", True, 9, "综合"),
    ("netease", "网易新闻", False, 10, "新闻"),
]


def log(message: str) -> None:
    print(f"[init] {message}")


def get_database_url() -> str:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is required")
    return database_url


def ensure_super_admins(cursor) -> None:
    if not SUPER_ADMIN_EMAILS:
        log("SUPER_ADMIN_EMAILS not configured, skipping super-admin provisioning")
        return

    for email in SUPER_ADMIN_EMAILS:
        cursor.execute(
            """
            SELECT id, email, membership_tier, is_superuser
            FROM users
            WHERE email = %s
            """,
            (email,),
        )
        user = cursor.fetchone()
        if not user:
            log(f"super-admin email not found in users table, skipping create: {email}")
            continue

        target_tier = "superuser"
        if user["is_superuser"] and user["membership_tier"] == target_tier:
            log(f"super-admin flags already healthy for {email}")
            continue

        cursor.execute(
            """
            UPDATE users
            SET is_superuser = TRUE,
                membership_tier = %s,
                updated_at = NOW()
            WHERE id = %s
            """,
            (target_tier, user["id"]),
        )
        log(f"repaired super-admin flags for {email} (tier={target_tier})")


def ensure_tier_defaults(cursor) -> None:
    for tier, (chat_model, writer_model, article_limit) in DEFAULT_TIER_MODELS.items():
        cursor.execute(
            """
            INSERT INTO tier_default_models (tier, default_chat_model, default_writer_model, article_limit_per_month, updated_at)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (tier)
            DO NOTHING
            """,
            (tier, chat_model, writer_model, article_limit, datetime.now(timezone.utc)),
        )
    log("ensured tier default models")


def ensure_hotspot_sources(cursor) -> None:
    cursor.execute("SELECT COUNT(*) FROM hotspot_sources")
    count = cursor.fetchone()["count"]
    if count and count > 0:
        log("hotspot sources already present")
        return

    for source_id, name, enabled, sort_order, category in DEFAULT_HOTSPOT_SOURCES:
        cursor.execute(
            """
            INSERT INTO hotspot_sources (id, name, enabled, sort_order, category)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
            """,
            (source_id, name, enabled, sort_order, category),
        )
    log("seeded hotspot sources")


def ensure_global_providers(cursor) -> None:
    cursor.execute("SELECT COUNT(*) FROM global_llm_providers")
    count = cursor.fetchone()["count"]
    if count and count > 0:
        log("global llm providers already present")
        return

    cursor.execute(
        """
        SELECT provider_id, provider_name, base_url, default_models
        FROM llm_provider_templates
        WHERE is_active = TRUE
        ORDER BY provider_id
        """
    )
    templates = cursor.fetchall()
    if not templates:
        log("no active llm provider templates found, skipping provider seeding")
        return

    for row in templates:
        default_models = row["default_models"] or []
        models = [
            {"name": model_name, "min_tier": "free"}
            for model_name in default_models
        ]
        cursor.execute(
            """
            INSERT INTO global_llm_providers (
                provider_id,
                provider_name,
                base_url,
                api_key_encrypted,
                models,
                enabled,
                created_at,
                updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
            ON CONFLICT (provider_id) DO NOTHING
            """,
            (
                row["provider_id"],
                row["provider_name"],
                row["base_url"],
                None,
                Json(models),
                False,
            ),
        )
    log("seeded global llm providers from templates")


def main() -> int:
    conn = psycopg2.connect(get_database_url(), cursor_factory=RealDictCursor)
    try:
        with conn:
            with conn.cursor() as cursor:
                ensure_super_admins(cursor)
                ensure_tier_defaults(cursor)
                ensure_hotspot_sources(cursor)
                ensure_global_providers(cursor)
        log("production state initialization complete")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
