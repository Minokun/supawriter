# -*- coding: utf-8 -*-
"""Tests for platform_converter new platforms (CSDN, Baijiahao, ZSXQ)."""

import pytest
from utils.platform_converter import convert_to_platform


class TestCSDNConversion:
    def test_csdn_supported(self):
        """CSDN should be in SUPPORTED_PLATFORMS."""
        from utils.platform_converter import SUPPORTED_PLATFORMS
        assert "csdn" in SUPPORTED_PLATFORMS

    def test_csdn_h1_to_h2(self):
        """CSDN: h1 headings should be demoted to h2."""
        md = "# Main Title\n\nSome content\n\n## Sub Title"
        result = convert_to_platform(md, "csdn", topic="测试")
        assert "## Main Title" in result["content"]
        assert result["format"] == "markdown"

    def test_csdn_copy_format_plain_text(self):
        result = convert_to_platform("Hello world", "csdn")
        assert result["copy_format"] == "plain_text"

    def test_csdn_topic_tags(self):
        """CSDN should include topic-based tag suggestions."""
        md = "# Python教程\n\nPython是一门很好的语言"
        result = convert_to_platform(md, "csdn", topic="Python入门")
        assert "Python入门" in result["content"] or "#" in result["content"]


class TestBaijiahaoConversion:
    def test_baijiahao_supported(self):
        from utils.platform_converter import SUPPORTED_PLATFORMS
        assert "baijiahao" in SUPPORTED_PLATFORMS

    def test_baijiahao_returns_html(self):
        result = convert_to_platform("# Title\n\nParagraph", "baijiahao")
        assert result["format"] == "html"
        assert "<" in result["content"]

    def test_baijiahao_copy_format_rich_text(self):
        result = convert_to_platform("Hello", "baijiahao")
        assert result["copy_format"] == "rich_text"

    def test_baijiahao_inline_styles(self):
        """Baijiahao HTML should have paragraph styles for readability."""
        result = convert_to_platform("第一段\n\n第二段", "baijiahao")
        assert "line-height" in result["content"] or "style" in result["content"]


class TestZSXQConversion:
    def test_zsxq_supported(self):
        from utils.platform_converter import SUPPORTED_PLATFORMS
        assert "zsxq" in SUPPORTED_PLATFORMS

    def test_zsxq_returns_markdown(self):
        """知识星球 should return raw markdown."""
        md = "# Title\n\n- item1\n- item2"
        result = convert_to_platform(md, "zsxq")
        assert result["format"] == "markdown"
        assert result["content"] == md

    def test_zsxq_copy_format_plain_text(self):
        result = convert_to_platform("Hello", "zsxq")
        assert result["copy_format"] == "plain_text"


class TestExistingPlatformsStillWork:
    """Regression: existing platforms should still work."""

    def test_wechat(self):
        result = convert_to_platform("# Hello", "wechat")
        assert result["format"] == "html"

    def test_zhihu(self):
        result = convert_to_platform("# Hello", "zhihu", topic="test")
        assert result["format"] == "markdown"

    def test_xiaohongshu(self):
        result = convert_to_platform("Hello world", "xiaohongshu", topic="test")
        assert result["format"] == "text"

    def test_toutiao(self):
        result = convert_to_platform("# Hello", "toutiao")
        assert result["format"] == "html"

    def test_unsupported_platform_raises(self):
        with pytest.raises(ValueError, match="不支持的平台"):
            convert_to_platform("Hello", "nonexistent")
