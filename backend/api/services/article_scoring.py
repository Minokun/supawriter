# -*- coding: utf-8 -*-
"""
文章质量评分服务（F4 功能）

实现4维度评分：
1. 可读性 - 基于规则的文本分析
2. 信息密度 - LLM分析内容信息量
3. SEO友好度 - LLM分析关键词、标题优化建议
4. 传播力 - LLM分析标题吸引度、话题热度
"""

import re
import json
import logging
from typing import Dict, List, Any
from datetime import datetime
from backend.api.services.llm_client import LLMClient

logger = logging.getLogger(__name__)


class ArticleScoringService:
    """文章质量评分服务"""

    # 评分等级阈值
    LEVEL_THRESHOLDS = {
        'excellent': 85,  # 85-100
        'good': 70,      # 70-84
        'average': 50,    # 50-69
        'poor': 0         # 0-49
    }

    # 各维度权重
    DIMENSION_WEIGHTS = {
        'readability': 0.30,      # 可读性 30%
        'information_density': 0.25,  # 信息密度 25%
        'seo': 0.20,               # SEO 20%
        'virality': 0.25            # 传播力 25%
    }

    @classmethod
    def calculate_readability_score(cls, content: str) -> Dict[str, Any]:
        """
        计算可读性评分（基于规则）

        评分标准：
        - 段落长度：每段50-200字最佳
        - 句子长度：每句10-40字最佳
        - 标题层次：是否合理使用标题
        - 列表使用：是否使用列表提高可读性
        - 总字数：800-3000字最佳
        """
        if not content:
            return {'score': 0, 'suggestions': ['文章内容为空']}

        suggestions = []
        score = 100

        # 1. 总字数检查
        word_count = len(content.strip())
        if word_count < 300:
            score -= 20
            suggestions.append('文章过短，建议补充更多内容达到300字以上')
        elif word_count < 800:
            score -= 10
            suggestions.append('文章较短，建议扩展到800字以上获得更好可读性')
        elif word_count > 5000:
            score -= 15
            suggestions.append('文章过长，建议拆分为多篇')
        elif word_count > 3000:
            score -= 5
            suggestions.append('文章较长，建议使用更多小标题分段')

        # 2. 段落长度检查
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        if paragraphs:
            avg_para_length = sum(len(p) for p in paragraphs) / len(paragraphs)
            if avg_para_length > 400:
                score -= 10
                suggestions.append('段落过长，建议缩短每段长度到400字以内')
            elif avg_para_length < 50:
                score -= 5
                suggestions.append('段落过短，建议适当合并段落')

        # 3. 句子长度检查
        sentences = re.split(r'[。！？；]', content)
        if sentences:
            long_sentences = [s for s in sentences if len(s.strip()) > 50]
            if len(long_sentences) > len(sentences) * 0.3:
                score -= 10
                suggestions.append('长句过多，建议使用短句提高可读性')

        # 4. 标题层次检查
        h1_count = content.count('# ')
        h2_count = content.count('## ')
        h3_count = content.count('### ')

        if h1_count == 0 and h2_count == 0:
            score -= 15
            suggestions.append('缺少标题层级，建议使用二级标题(##)分段')
        elif h1_count > 1:
            score -= 10
            suggestions.append('一级标题(# )过多，每篇文章只需一个')
        elif h2_count == 0 and word_count > 1000:
            score -= 5
            suggestions.append('文章较长，建议使用二级标题分段')

        # 5. 列表使用检查
        bullet_lines = len(re.findall(r'^[\-\*]\s', content, re.MULTILINE))
        if bullet_lines == 0 and word_count > 500:
            score -= 5
            suggestions.append('建议使用列表(- )展示关键信息')

        # 6. 代码块检查
        code_blocks = len(re.findall(r'```', content)) // 2
        if code_blocks > 3:
            score -= 5
            suggestions.append('代码块过多，可能影响普通读者阅读')

        # 确保分数在0-100范围内
        score = max(0, min(100, score))

        return {
            'name': 'readability',
            'label': '可读性',
            'score': score,
            'weight': cls.DIMENSION_WEIGHTS['readability'],
            'suggestions': suggestions[:3]  # 最多返回3条建议
        }

    @classmethod
    async def calculate_information_density_score(cls, content: str, title: str = "") -> Dict[str, Any]:
        """
        计算信息密度评分（基于LLM）

        分析维度：
        - 信息量：文章是否有实质内容
        - 深度：内容是否有深度分析
        - 独特性：内容是否有独特观点
        """
        if not content:
            return {
                'name': 'information_density',
                'label': '信息密度',
                'score': 50,
                'weight': cls.DIMENSION_WEIGHTS['information_density'],
                'suggestions': ['内容为空']
            }

        try:
            llm = LLMClient()

            prompt = f"""请分析以下文章的信息密度，从以下3个维度评分（0-100分）：

文章标题：{title}
文章内容：{content[:2000]}...

评分标准：
1. 信息量：文章是否有实质内容和有用信息
2. 深度：内容是否有深度分析和独到见解
3. 独特性：内容是否有独特观点或新信息

请以JSON格式返回，格式：
{{
  "score": 总分(0-100),
  "information_volume": {{ "score": 信息量分数, "comment": "评价" }},
  "depth": {{ "score": 深度分数, "comment": "评价" }},
  "uniqueness": {{ "score": 独特性分数, "comment": "评价" }},
  "suggestions": ["建议1", "建议2", "建议3"]
}}"""

            response = await llm.chat_completion(
                prompt=prompt,
                temperature=0.3
            )

            # 解析LLM响应
            result = json.loads(response)

            score = result.get('score', 70)
            suggestions = result.get('suggestions', [])

            return {
                'name': 'information_density',
                'label': '信息密度',
                'score': score,
                'weight': cls.DIMENSION_WEIGHTS['information_density'],
                'suggestions': suggestions[:3]
            }

        except Exception as e:
            logger.error(f"LLM信息密度分析失败: {e}")
            # 返回默认评分
            return {
                'name': 'information_density',
                'label': '信息密度',
                'score': 70,
                'weight': cls.DIMENSION_WEIGHTS['information_density'],
                'suggestions': ['信息密度分析暂时不可用']
            }

    @classmethod
    async def calculate_seo_score(cls, content: str, title: str = "") -> Dict[str, Any]:
        """
        计算SEO友好度评分（基于LLM）

        分析维度：
        - 关键词：是否包含核心关键词
        - 标题优化：标题是否吸引且含关键词
        - 结构优化：是否有合理的段落结构
        """
        if not content:
            return {
                'name': 'seo',
                'label': 'SEO友好度',
                'score': 50,
                'weight': cls.DIMENSION_WEIGHTS['seo'],
                'suggestions': ['内容为空']
            }

        try:
            llm = LLMClient()

            prompt = f"""请分析以下文章的SEO友好度，从以下3个维度评分（0-100分）：

文章标题：{title}
文章内容：{content[:2000]}...

评分标准：
1. 关键词：内容是否包含核心关键词和热点话题词
2. 标题优化：标题是否吸引且含关键词，利于搜索排名
3. 结构优化：是否有合理的段落结构和标签使用

请以JSON格式返回，格式：
{{
  "score": 总分(0-100),
  "keywords": {{ "score": 关键词分数, "comment": "评价" }},
  "title_optimization": {{ "score": 标题优化分数, "comment": "评价" }},
  "structure": {{ "score": 结构优化分数, "comment": "评价" }},
  "suggestions": ["建议1", "建议2", "建议3"]
}}"""

            response = await llm.chat_completion(
                prompt=prompt,
                temperature=0.3
            )

            # 解析LLM响应
            result = json.loads(response)

            score = result.get('score', 70)
            suggestions = result.get('suggestions', [])

            return {
                'name': 'seo',
                'label': 'SEO友好度',
                'score': score,
                'weight': cls.DIMENSION_WEIGHTS['seo'],
                'suggestions': suggestions[:3]
            }

        except Exception as e:
            logger.error(f"LLM SEO分析失败: {e}")
            return {
                'name': 'seo',
                'label': 'SEO友好度',
                'score': 70,
                'weight': cls.DIMENSION_WEIGHTS['seo'],
                'suggestions': ['SEO分析暂时不可用']
            }

    @classmethod
    async def calculate_virality_score(cls, content: str, title: str = "") -> Dict[str, Any]:
        """
        计算传播力评分（基于LLM）

        分析维度：
        - 标题吸引度：标题是否吸引点击
        - 话题热度：内容涉及的话题热度
        - 分享价值：内容是否有分享价值
        """
        if not content:
            return {
                'name': 'virality',
                'label': '传播力',
                'score': 50,
                'weight': cls.DIMENSION_WEIGHTS['virality'],
                'suggestions': ['内容为空']
            }

        try:
            llm = LLMClient()

            prompt = f"""请分析以下文章的传播力，从以下3个维度评分（0-100分）：

文章标题：{title}
文章内容：{content[:2000]}...

评分标准：
1. 标题吸引度：标题是否吸引点击，引发好奇心
2. 话题热度：内容涉及的话题是否有传播潜力
3. 分享价值：内容是否有被转发和分享的价值

请以JSON格式返回，格式：
{{
  "score": 总分(0-100),
  "title_appeal": {{ "score": 标题吸引度分数, "comment": "评价" }},
  "topic_trend": {{ "score": 话题热度分数, "comment": "评价" }},
  "share_value": {{ "score": 分享价值分数, "comment": "评价" }},
  "suggestions": ["建议1", "建议2", "建议3"]
}}"""

            response = await llm.chat_completion(
                prompt=prompt,
                temperature=0.3
            )

            # 解析LLM响应
            result = json.loads(response)

            score = result.get('score', 70)
            suggestions = result.get('suggestions', [])

            return {
                'name': 'virality',
                'label': '传播力',
                'score': score,
                'weight': cls.DIMENSION_WEIGHTS['virality'],
                'suggestions': suggestions[:3]
            }

        except Exception as e:
            logger.error(f"LLM传播力分析失败: {e}")
            return {
                'name': 'virality',
                'label': '传播力',
                'score': 70,
                'weight': cls.DIMENSION_WEIGHTS['virality'],
                'suggestions': ['传播力分析暂时不可用']
            }
    @classmethod
    def calculate_total_score(cls, dimensions: List[Dict[str, Any]]) -> int:
        """
        计算总分

        Args:
            dimensions: 4个维度的评分结果

        Returns:
            总分 0-100
        """
        total = sum(d['score'] * d['weight'] for d in dimensions)
        return round(total)

    @classmethod
    def get_level(cls, total_score: int) -> str:
        """
        根据总分获取等级

        Args:
            total_score: 总分 0-100

        Returns:
            等级: excellent/good/average/poor
        """
        for level, threshold in sorted(
            cls.LEVEL_THRESHOLDS.items(),
            key=lambda x: -x[1]
        ):
            if total_score >= threshold:
                return level
        return 'poor'

    @classmethod
    def get_level_label(cls, level: str) -> str:
        """获取等级显示标签"""
        labels = {
            'excellent': '优秀 🌟',
            'good': '良好 👍',
            'average': '一般 ⚖️',
            'poor': '需改进 ⚠️'
        }
        return labels.get(level, level)

    @classmethod
    def generate_summary(cls, total_score: int, level: str, dimensions: List[Dict[str, Any]]) -> str:
        """
        生成评分总结

        Args:
            total_score: 总分
            level: 等级
            dimensions: 各维度评分

        Returns:
            一句话评语
        """
        if total_score >= 85:
            return '这是一篇高质量文章，结构清晰，内容充实！'
        elif total_score >= 70:
            return '文章整体质量不错，有少量可优化空间。'
        elif total_score >= 50:
            return '文章内容尚可，建议优化结构和表达。'
        else:
            return '文章需要较大改进，请参考下方建议。'

    @classmethod
    def get_level_color(cls, level: str) -> str:
        """获取等级颜色（用于前端展示）"""
        colors = {
            'excellent': 'green',
            'good': 'blue',
            'average': 'yellow',
            'poor': 'red'
        }
        return colors.get(level, 'gray')


# 评分结果数据模型
class ScoreResult:
    """评分结果"""

    def __init__(
        self,
        article_id: str,
        total_score: int,
        level: str,
        summary: str,
        dimensions: List[Dict[str, Any]],
        scored_at: datetime = None
    ):
        self.article_id = article_id
        self.total_score = total_score
        self.level = level
        self.summary = summary
        self.dimensions = dimensions
        self.scored_at = scored_at or datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'article_id': self.article_id,
            'total_score': self.total_score,
            'level': self.level,
            'summary': self.summary,
            'dimensions': self.dimensions,
            'scored_at': self.scored_at.isoformat() if self.scored_at else None
        }
