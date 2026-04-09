# -*- coding: utf-8 -*-
"""水印注入工具。

设计原则：
- 水印在输出时注入，不写入数据库原文。
- 仅免费用户（free）注入，pro/ultra 不注入。
- 支持 markdown 和 html 输出格式。
"""

from typing import Literal


MARKDOWN_WATERMARK = "---\n本文由 [SupaWriter](https://supawriter.com?ref=watermark) AI 辅助创作"
HTML_WATERMARK = (
    '<div style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #e0e0e0; '
    'text-align: center; color: #999; font-size: 12px;">'
    '本文由 <a href="https://supawriter.com?ref=watermark" '
    'style="color: #10b981; text-decoration: none;">SupaWriter</a> AI 辅助创作'
    "</div>"
)


def should_inject_watermark(user_tier: str) -> bool:
    """免费用户注入水印，付费用户不注入。"""
    return user_tier not in ("pro", "ultra")


def _inject_markdown_watermark(content: str) -> str:
    if "supawriter.com?ref=watermark" in content:
        return content

    base = content.rstrip()
    if not base:
        return MARKDOWN_WATERMARK
    return f"{base}\n\n{MARKDOWN_WATERMARK}"


def _inject_html_watermark(content: str) -> str:
    if "supawriter.com?ref=watermark" in content:
        return content
    return f"{content}{HTML_WATERMARK}"


def inject_watermark_if_needed(
    content: str,
    user_tier: str,
    format: Literal["markdown", "html"] = "markdown",
) -> str:
    """按用户等级条件性注入水印。"""
    if not content:
        return content

    if not should_inject_watermark(user_tier):
        return content

    if format == "html":
        return _inject_html_watermark(content)

    return _inject_markdown_watermark(content)
