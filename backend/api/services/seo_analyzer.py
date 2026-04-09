# -*- coding: utf-8 -*-
"""
SEO优化引擎服务（P1 F7 功能）

实现功能：
1. 关键词提取 - LLM分析提取核心关键词
2. 密度计算 - 计算关键词在文章中的出现频率
3. 标题优化 - LLM生成优化建议标题
4. 元描述 - LLM生成SEO元描述
5. 内链建议 - 基于用户历史文章匹配
"""

import json
import logging
import re
from typing import Dict, List, Any, Optional
from collections import Counter

from backend.api.services.llm_client import LLMClient
from utils.database import Database

logger = logging.getLogger(__name__)


class SEOAnalyzerService:
    """SEO分析服务"""

    # 关键词密度标准
    KEYWORD_DENSITY_TARGETS = {
        'good': (2.0, 3.5),   # 2-3.5% 为最佳
        'acceptable': (1.0, 4.5),  # 1-4.5% 可接受
        'low': (0, 1.0),        # 低于1%过低
        'high': (4.5, 100)      # 高于4.5%过高
    }

    @classmethod
    async def extract_keywords(cls, content: str, title: str = "", count: int = 5) -> List[Dict[str, Any]]:
        """
        提取核心关键词（LLM方式）

        Args:
            content: 文章内容
            title: 文章标题
            count: 提取关键词数量

        Returns:
            关键词列表，包含关键词和相关性分数
        """
        if not content:
            return []

        try:
            llm = LLMClient()

            prompt = f"""请分析以下文章，提取{count}个最核心的关键词。

文章标题：{title}
文章内容：{content[:2000]}...

要求：
1. 提取最能代表文章主题的关键词
2. 关键词应该是2-4个字的词组
3. 按重要性排序，最重要的在前
4. 每个关键词给出相关性评分（0-100）

请以JSON格式返回：
{{
  "keywords": [
    {{"word": "关键词1", "relevance": 95}},
    {{"word": "关键词2", "relevance": 85}},
    ...
  ]
}}"""

            response = await llm.chat_completion(
                prompt=prompt,
                temperature=0.3
            )

            result = json.loads(response)
            keywords = result.get('keywords', [])

            return keywords

        except Exception as e:
            logger.error(f"LLM关键词提取失败: {e}")
            # Fallback: 简单规则提取
            return cls._extract_keywords_fallback(content)

    @classmethod
    def _extract_keywords_fallback(cls, content: str) -> List[Dict[str, Any]]:
        """
        规则方式提取关键词（Fallback）

        基于简单的词频统计
        """
        # 移除标点符号和特殊字符
        content = re.sub(r'[^\w\s]', '', content)

        # 提取中文词汇（简单按空格和标点分割）
        words = re.findall(r'[\u4e00-\u9fa5]{2,4}', content)

        # 统计词频
        word_freq = Counter(words)

        # 排除常见停用词
        stopwords = {'这个', '那个', '可以', '应该', '如果', '但是', '因为', '所以', '还有', '就是', '我们', '他们', '自己', '时候', '可能', '需要', '这种'}
        for word in stopwords:
            if word in word_freq:
                del word_freq[word]

        # 返回前5个高频词
        top_words = word_freq.most_common(5)

        return [
            {"word": word, "relevance": min(90, 30 + i * 10)}
            for i, (word, freq) in enumerate(top_words)
        ]

    @classmethod
    def calculate_keyword_density(cls, content: str, keyword: str) -> Dict[str, Any]:
        """
        计算关键词密度

        Args:
            content: 文章内容
            keyword: 关键词

        Returns:
            密度信息，包含百分比、状态、建议
        """
        if not content or not keyword:
            return {
                'keyword': keyword,
                'density': 0.0,
                'count': 0,
                'status': 'unknown',
                'suggestion': '无效输入'
            }

        # 统计关键词出现次数
        content_lower = content.lower()
        keyword_lower = keyword.lower()

        # 使用正则表达式匹配完整词
        pattern = r'\b' + re.escape(keyword_lower) + r'\b'
        count = len(re.findall(pattern, content_lower))

        # 计算密度（关键词字符数 / 文章总字符数 * 100）
        # 注意：这里简化计算，实际应该用词数
        density = (count * len(keyword) / len(content)) * 100

        # 判断密度状态
        if cls.KEYWORD_DENSITY_TARGETS['good'][0] <= density <= cls.KEYWORD_DENSITY_TARGETS['good'][1]:
            status = 'good'
            suggestion = '密度适中，符合SEO最佳实践'
            color = 'green'
        elif cls.KEYWORD_DENSITY_TARGETS['acceptable'][0] <= density <= cls.KEYWORD_DENSITY_TARGETS['acceptable'][1]:
            status = 'acceptable'
            suggestion = '密度可接受，可适当调整'
            color = 'yellow'
        elif density < cls.KEYWORD_DENSITY_TARGETS['low'][1]:
            status = 'low'
            suggestion = '密度过低，建议增加关键词出现频率'
            color = 'red'
        else:
            status = 'high'
            suggestion = '密度过高，可能被视为关键词堆砌'
            color = 'red'

        return {
            'keyword': keyword,
            'density': round(density, 2),
            'count': count,
            'status': status,
            'color': color,
            'suggestion': suggestion
        }

    @classmethod
    async def optimize_title(cls, content: str, current_title: str = "") -> Dict[str, Any]:
        """
        标题优化（LLM方式）

        Args:
            content: 文章内容
            current_title: 当前标题

        Returns:
            优化建议，包括评分和3个优化标题
        """
        if not content:
            return {
                'score': 50,
                'current_title': current_title,
                'suggestions': [],
                'feedback': '内容为空，无法分析'
            }

        try:
            llm = LLMClient()

            prompt = f"""请对以下文章的标题进行SEO优化分析。

当前标题：{current_title}
文章内容：{content[:2000]}...

请从以下维度对当前标题进行评分（0-100分）：
1. 吸引力：标题是否吸引点击
2. 关键词：是否包含核心关键词
3. 长度：标题长度是否合适（建议15-30字）
4. 情感：是否能引起读者共鸣

并生成3个优化后的标题建议。

请以JSON格式返回：
{{
  "score": 当前标题评分(0-100),
  "feedback": "当前标题评价和建议",
  "optimized_titles": [
    {{"title": "优化标题1", "reason": "优化原因1"}},
    {{"title": "优化标题2", "reason": "优化原因2"}},
    {{"title": "优化标题3", "reason": "优化原因3"}}
  ]
}}"""

            response = await llm.chat_completion(
                prompt=prompt,
                temperature=0.7
            )

            result = json.loads(response)

            return {
                'score': result.get('score', 70),
                'current_title': current_title,
                'feedback': result.get('feedback', '暂无评价'),
                'suggestions': result.get('optimized_titles', [])
            }

        except Exception as e:
            logger.error(f"LLM标题优化失败: {e}")
            return {
                'score': 70,
                'current_title': current_title,
                'feedback': '标题优化暂时不可用',
                'suggestions': []
            }

    @classmethod
    async def generate_meta_description(cls, content: str, title: str = "") -> Dict[str, Any]:
        """
        生成SEO元描述（LLM方式）

        Args:
            content: 文章内容
            title: 文章标题

        Returns:
            元描述，包含内容和长度信息
        """
        if not content:
            return {
                'description': '',
                'length': 0,
                'status': 'error',
                'suggestion': '内容为空'
            }

        try:
            llm = LLMClient()

            prompt = f"""请为以下文章生成SEO友好的元描述（meta description）。

文章标题：{title}
文章内容：{content[:2000]}...

要求：
1. 长度在120-160个字符之间
2. 包含文章的核心关键词
3. 清晰描述文章内容和价值
4. 吸引读者点击

请直接返回元描述文本，不要包含任何其他内容。"""

            response = await llm.chat_completion(
                prompt=prompt,
                temperature=0.5
            )

            # 清理响应
            description = response.strip()

            # 检查是否是 LLM 错误响应（JSON格式）
            try:
                parsed = json.loads(description)
                if isinstance(parsed, dict) and 'score' in parsed and 'suggestions' in parsed:
                    # 这是错误响应，使用 fallback
                    raise Exception("LLM returned error response")
            except json.JSONDecodeError:
                # 不是 JSON，正常处理
                pass

            # 移除引号（如果有）
            if description.startswith('"') and description.endswith('"'):
                description = description[1:-1]
            elif description.startswith("'") and description.endswith("'"):
                description = description[1:-1]

            length = len(description)

            # 检查长度
            if 120 <= length <= 160:
                status = 'good'
                color = 'green'
                suggestion = '长度适中，符合SEO最佳实践'
            elif 100 <= length < 120 or 160 < length <= 180:
                status = 'acceptable'
                color = 'yellow'
                suggestion = '长度基本可接受，可适当调整'
            else:
                status = 'needs_improvement'
                color = 'red'
                suggestion = '长度需要调整，建议在120-160字符之间'

            return {
                'description': description,
                'length': length,
                'status': status,
                'color': color,
                'suggestion': suggestion
            }

        except Exception as e:
            logger.error(f"LLM元描述生成失败: {e}")
            return {
                'description': content[:150] + '...',
                'length': min(153, len(content)),
                'status': 'fallback',
                'color': 'gray',
                'suggestion': '使用前150字作为默认描述'
            }

    @classmethod
    async def get_internal_link_suggestions(
        cls,
        content: str,
        user_id: int,
        article_id: Optional[str] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        基于用户历史文章生成内链建议

        Args:
            content: 当前文章内容
            user_id: 用户ID
            article_id: 当前文章ID（排除当前文章）
            limit: 返回建议数量

        Returns:
            内链建议列表
        """
        try:
            # 获取用户历史文章（排除当前文章）
            query = """
                SELECT id, title, content, created_at
                FROM articles
                WHERE user_id = %s
                AND id != %s
                AND content IS NOT NULL
                ORDER BY created_at DESC
                LIMIT 50
            """

            with Database.get_cursor() as cursor:
                cursor.execute(query, (user_id, article_id or ''))
                articles = cursor.fetchall()

            if not articles:
                return []

            # 提取当前文章关键词
            keywords = await cls.extract_keywords(content)
            keyword_list = [k['word'] for k in keywords]

            # 使用关键词进行相关性匹配
            suggestions = []

            for article in articles:
                article_id_str = str(article.get('id', ''))
                title = article.get('title', '') or ''
                article_content = article.get('content', '') or ''

                # 简单关键词匹配
                match_count = 0
                for keyword in keyword_list:
                    if keyword in title or keyword in article_content:
                        match_count += 1

                if match_count > 0:
                    suggestions.append({
                        'article_id': article_id_str,
                        'title': title,
                        'relevance': min(95, 60 + match_count * 10),
                        'reason': f'包含{match_count}个相关关键词',
                        'suggested_anchor_text': keyword_list[0] if keyword_list else title
                    })

            # 按相关性排序
            suggestions.sort(key=lambda x: x['relevance'], reverse=True)

            # 返回前N个建议
            return suggestions[:limit]

        except Exception as e:
            logger.error(f"内链建议生成失败: {e}")
            return []

    @classmethod
    async def analyze_seo(
        cls,
        content: str,
        title: str = "",
        user_id: Optional[int] = None,
        article_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        完整的SEO分析

        Args:
            content: 文章内容
            title: 文章标题
            user_id: 用户ID
            article_id: 文章ID

        Returns:
            完整的SEO分析结果
        """
        # 1. 提取关键词
        keywords = await cls.extract_keywords(content, title, count=5)

        # 2. 计算关键词密度
        keyword_analysis = []
        for kw in keywords:
            density_info = cls.calculate_keyword_density(content, kw['word'])
            keyword_analysis.append({
                'keyword': kw['word'],
                'relevance': kw['relevance'],
                'density': density_info
            })

        # 3. 标题优化建议
        title_optimization = await cls.optimize_title(content, title)

        # 4. 元描述生成
        meta_description = await cls.generate_meta_description(content, title)

        # 5. 内链建议（如果提供了user_id）
        internal_links = []
        if user_id:
            internal_links = await cls.get_internal_link_suggestions(
                content, user_id, article_id, limit=5
            )

        # 6. 计算总体评分
        seo_score = cls._calculate_seo_score(
            keyword_analysis,
            title_optimization,
            meta_description
        )

        return {
            'seo_score': seo_score,
            'keywords': keyword_analysis,
            'title_optimization': title_optimization,
            'meta_description': meta_description,
            'internal_links': internal_links
        }

    @classmethod
    def _calculate_seo_score(
        cls,
        keywords: List[Dict[str, Any]],
        title_opt: Dict[str, Any],
        meta_desc: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        计算总体SEO评分

        Args:
            keywords: 关键词分析结果
            title_opt: 标题优化结果
            meta_desc: 元描述结果

        Returns:
            SEO评分信息
        """
        score = 0
        feedback = []

        # 1. 关键词评分（40%权重）
        keyword_score = 0
        good_density_count = 0
        for kw in keywords:
            density_info = kw['density']
            if density_info['status'] == 'good':
                good_density_count += 1
            elif density_info['status'] == 'acceptable':
                good_density_count += 0.5

        if keywords:
            keyword_score = (good_density_count / len(keywords)) * 100
        score += keyword_score * 0.4

        if keyword_score >= 80:
            feedback.append('关键词密度分布良好')
        elif keyword_score >= 60:
            feedback.append('关键词密度基本合理，可适当调整')
        else:
            feedback.append('关键词密度需要优化')

        # 2. 标题评分（35%权重）
        title_score = title_opt.get('score', 70)
        score += title_score * 0.35

        if title_score >= 85:
            feedback.append('标题SEO表现优秀')
        elif title_score >= 70:
            feedback.append('标题基本符合SEO要求')
        else:
            feedback.append('标题需要优化')

        # 3. 元描述评分（25%权重）
        meta_score = 100
        if meta_desc.get('status') == 'good':
            meta_score = 100
        elif meta_desc.get('status') == 'acceptable':
            meta_score = 80
        elif meta_desc.get('status') == 'needs_improvement':
            meta_score = 60
        else:
            meta_score = 50

        score += meta_score * 0.25

        if meta_score >= 90:
            feedback.append('元描述长度适中')
        elif meta_score >= 70:
            feedback.append('元描述长度基本可接受')
        else:
            feedback.append('元描述长度需要调整')

        # 四舍五入
        score = round(score)

        # 确定等级
        if score >= 85:
            level = 'excellent'
            level_label = '优秀 🌟'
            color = 'green'
        elif score >= 70:
            level = 'good'
            level_label = '良好 👍'
            color = 'blue'
        elif score >= 50:
            level = 'average'
            level_label = '一般 ⚖️'
            color = 'yellow'
        else:
            level = 'poor'
            level_label = '需改进 ⚠️'
            color = 'red'

        return {
            'score': score,
            'level': level,
            'level_label': level_label,
            'color': color,
            'feedback': feedback
        }
