# -*- coding: utf-8 -*-
"""
多平台格式转换工具 (F3 功能）

支持：微信公众号、知乎、小红书、今日头条
"""

import re
from typing import Any, Dict, List
import markdown
from utils.wechat_converter import markdown_to_wechat_html

SUPPORTED_PLATFORMS = {"wechat", "zhihu", "xiaohongshu", "toutiao", "csdn", "baijiahao", "zsxq"}


def _word_count(text: str) -> int:
    return len((text or "").strip())


def _extract_topic_tags(topic: str, content: str, limit: int = 5) -> List[str]:
    """提取话题标签"""
    tags: List[str] = []
    if topic:
        tags.append(f"#{topic}#")

    # 中文词块提取
    candidates = re.findall(r"[\u4e00-\u9fff]{2,8}", content or "")
    seen = set()
    for word in candidates:
        if word in seen:
            continue
        seen.add(word)
        if len(word) < 2:
            continue
        tags.append(f"#{word}#")
        if len(tags) >= limit:
            break
    return tags[:limit]


def _convert_wechat(content: str) -> Dict[str, Any]:
    """转换为微信公众号格式"""
    html = markdown_to_wechat_html(content, style="wechat")
    return {
        "content": html,
        "format": "html",
        "tags": [],
        "word_count": _word_count(content),
        "copy_format": "rich_text",
    }


def _convert_zhihu(content: str, topic: str) -> Dict[str, Any]:
    """转换为知乎格式"""
    lines = (content or "").split("\n")
    converted: List[str] = []
    for line in lines:
        if line.startswith("# ") and not line.startswith("## "):
            converted.append("#" + line)  # h1 -> h2
        else:
            converted.append(line)

    result = "\n".join(converted).strip()
    tags = _extract_topic_tags(topic, result, limit=5)
    if tags:
        result = f"{result}\n\n---\n话题标签建议：\n" + " ".join(tags)

    return {
        "content": result,
        "format": "markdown",
        "tags": tags,
        "word_count": _word_count(result),
        "copy_format": "plain_text",
    }


def _strip_markdown_syntax(content: str) -> str:
    """清理Markdown语法"""
    text = content or ""
    # 移除代码块
    text = re.sub(r"```[\s\S]*?```", "", text)
    # 移除行内代码
    text = re.sub(r"`([^`]*)`", r"\1", text)
    # 移除链接语法
    text = re.sub(r"!\[[^\]]*\]\([^\)]*\)", "", text)
    # 移除强调语法
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    # 移除删除线
    text = re.sub(r"^~~.*~~$", "", text, flags=re.MULTILINE)
    # 移除Markdown标题标记 (# ## ### 等)
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    # 移除列表标记 (- * +)
    text = re.sub(r"^[-\*\+]\s+", "", text, flags=re.MULTILINE)
    # 移除多余的空行
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _convert_xiaohongshu(content: str, topic: str) -> Dict[str, Any]:
    """转换为小红书格式（含LLM改写）"""
    plain = _strip_markdown_syntax(content)
    trimmed = plain[:1200]

    paragraphs = [p.strip() for p in trimmed.split("\n") if p.strip()]
    if not paragraphs:
        paragraphs = ["今天分享一个实用观点，建议收藏。"]

    title = paragraphs[0]
    if len(title) > 28:
        title = title[:28].rstrip("，。？！；：")

    bullets = ["🔥", "💡", "✅", "📌"]
    body_lines: List[str] = [f"{bullets[0]} {title}"]
    for idx, p in enumerate(paragraphs[1:]):
        body_lines.append("")
        body_lines.append(f"{bullets[(idx + 1) % len(bullets)]} {p}")

    tags = _extract_topic_tags(topic or title, plain, limit=8)
    if tags:
        body_lines.append("")
        body_lines.append(" ".join(tags))

    result = "\n".join(body_lines).strip()

    return {
        "content": result,
        "format": "text",
        "tags": tags,
        "word_count": _word_count(result),
        "copy_format": "plain_text",
    }


def _convert_toutiao(content: str) -> Dict[str, Any]:
    """转换为今日头条格式"""
    html = markdown.markdown(
        content or "",
        extensions=["fenced_code", "tables", "nl2br", "sane_lists"],
    )

    # 头条偏好短段落阅读
    html = html.replace("<p>", '<p style="line-height:1.9;margin:12px 0;">')
    html = html.replace("<strong>", '<strong style="font-weight:700;color:#1f2937;">')

    return {
        "content": html,
        "format": "html",
        "tags": [],
        "word_count": _word_count(content),
        "copy_format": "rich_text",
    }


def _convert_csdn(content: str, topic: str) -> Dict[str, Any]:
    """转换为 CSDN 格式（Markdown，h1→h2，添加分类标签）"""
    lines = (content or "").split("\n")
    converted: List[str] = []
    for line in lines:
        if line.startswith("# ") and not line.startswith("## "):
            converted.append("#" + line)  # h1 -> h2
        else:
            converted.append(line)

    result = "\n".join(converted).strip()
    tags = _extract_topic_tags(topic, result, limit=5)
    if tags:
        result = f"{result}\n\n---\n分类标签建议：\n" + " ".join(tags)

    return {
        "content": result,
        "format": "markdown",
        "tags": tags,
        "word_count": _word_count(result),
        "copy_format": "plain_text",
    }


def _convert_baijiahao(content: str) -> Dict[str, Any]:
    """转换为百家号格式（HTML，短段落阅读样式）"""
    html = markdown.markdown(
        content or "",
        extensions=["fenced_code", "tables", "nl2br", "sane_lists"],
    )
    html = html.replace("<p>", '<p style="line-height:1.8;margin:15px 0;font-size:16px;">')
    html = html.replace("<strong>", '<strong style="font-weight:700;color:#1a1a1a;">')

    return {
        "content": html,
        "format": "html",
        "tags": [],
        "word_count": _word_count(content),
        "copy_format": "rich_text",
    }


def _convert_zsxq(content: str) -> Dict[str, Any]:
    """转换为知识星球格式（原始 Markdown）"""
    return {
        "content": content or "",
        "format": "markdown",
        "tags": [],
        "word_count": _word_count(content),
        "copy_format": "plain_text",
    }


def convert_to_platform(
    markdown_content: str,
    platform: str,
    topic: str = ""
) -> Dict[str, Any]:
    """
    将Markdown转换为指定平台格式

    Args:
        markdown_content: Markdown内容
        platform: 目标平台 (wechat/zhihu/xiaohongshu/toutiao)
        topic: 文章主题（用于生成话题标签）

    Returns:
        包含content, format, tags, word_count, copy_format的字典

    Raises:
        ValueError: 不支持的平台
    """
    platform_key = (platform or "wechat").lower()
    if platform_key not in SUPPORTED_PLATFORMS:
        raise ValueError(f"不支持的平台: {platform}")

    if platform_key == "wechat":
        return _convert_wechat(markdown_content)
    if platform_key == "zhihu":
        return _convert_zhihu(markdown_content, topic)
    if platform_key == "xiaohongshu":
        return _convert_xiaohongshu(markdown_content, topic)
    if platform_key == "toutiao":
        return _convert_toutiao(markdown_content)
    if platform_key == "csdn":
        return _convert_csdn(markdown_content, topic)
    if platform_key == "baijiahao":
        return _convert_baijiahao(markdown_content)
    return _convert_zsxq(markdown_content)
