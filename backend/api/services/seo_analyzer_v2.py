# -*- coding: utf-8 -*-
"""
SEO优化引擎服务 V2（合并LLM调用 + 数据库持久化）

优化点：
1. 单次LLM调用完成所有分析任务
2. 数据库存储结果
3. 后台异步处理
4. 先返回旧数据，后台更新新数据
"""

import json
import logging
import re
from typing import Dict, List, Any, Optional
from collections import Counter
from datetime import datetime

from backend.api.services.llm_client import LLMClient
from utils.database import Database
from backend.api.core.config import settings

logger = logging.getLogger(__name__)


class SEOAnalyzerServiceV2:
    """SEO分析服务 V2 - 优化版"""

    # 关键词密度标准
    KEYWORD_DENSITY_TARGETS = {
        'good': (2.0, 3.5),
        'acceptable': (1.0, 4.5),
        'low': (0, 1.0),
        'high': (4.5, 100)
    }

    @classmethod
    def ensure_table_exists(cls):
        """确保数据库表存在"""
        try:
            with Database.get_cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS article_seo_analysis (
                        id SERIAL PRIMARY KEY,
                        article_id VARCHAR(255) NOT NULL,
                        user_id INTEGER NOT NULL,
                        seo_score JSONB NOT NULL,
                        keywords JSONB NOT NULL,
                        title_optimization JSONB NOT NULL,
                        meta_description JSONB NOT NULL,
                        internal_links JSONB DEFAULT '[]',
                        is_analyzing BOOLEAN DEFAULT FALSE,
                        analysis_version INTEGER DEFAULT 1,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(article_id)
                    )
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_seo_analysis_article_id
                    ON article_seo_analysis(article_id)
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_seo_analysis_user_id
                    ON article_seo_analysis(user_id)
                """)
        except Exception as e:
            logger.error(f"创建SEO分析表失败: {e}")

    @classmethod
    async def analyze_all_in_one(
        cls,
        content: str,
        title: str = "",
        user_id: Optional[int] = None,
        article_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        单次LLM调用完成所有SEO分析

        Args:
            content: 文章内容
            title: 文章标题
            user_id: 用户ID
            article_id: 文章ID

        Returns:
            完整的SEO分析结果
        """
        if not content or len(content) < 50:
            return cls._get_default_result()

        try:
            llm = LLMClient()

            prompt = f"""请对以下文章进行完整的SEO分析，一次性返回所有结果。

文章标题：{title}
文章内容：{content[:3000]}...

请完成以下分析任务并返回JSON格式结果：

1. 关键词提取：提取5个最核心的关键词（2-4字词组），按重要性排序，给出相关性评分（0-100）

2. 标题优化：
   - 对当前标题评分（0-100），从吸引力、关键词覆盖、长度（15-30字）、情感共鸣四个维度
   - 给出评价和建议
   - 生成3个优化后的标题建议及原因

3. 元描述生成：生成120-160字符的SEO元描述，清晰描述文章内容和价值，吸引点击

请以以下JSON格式返回：
{{
  "keywords": [
    {{"word": "关键词1", "relevance": 95}},
    {{"word": "关键词2", "relevance": 85}}
  ],
  "title_analysis": {{
    "score": 当前标题评分,
    "feedback": "当前标题评价和建议",
    "optimized_titles": [
      {{"title": "优化标题1", "reason": "优化原因1"}},
      {{"title": "优化标题2", "reason": "优化原因2"}},
      {{"title": "优化标题3", "reason": "优化原因3"}}
    ]
  }},
  "meta_description": {{
    "description": "生成的元描述文本",
    "length": 字符数
  }}
}}"""

            response = await llm.chat_completion(
                prompt=prompt,
                temperature=0.5
            )

            result = json.loads(response)

            # 处理关键词密度
            keywords_with_density = []
            for kw in result.get('keywords', []):
                density_info = cls.calculate_keyword_density(content, kw['word'])
                keywords_with_density.append({
                    'keyword': kw['word'],
                    'relevance': kw['relevance'],
                    'density': density_info
                })

            # 处理元描述
            meta = result.get('meta_description', {})
            desc = meta.get('description', '')
            length = len(desc)
            if 120 <= length <= 160:
                status, color, suggestion = 'good', 'green', '长度适中，符合SEO最佳实践'
            elif 100 <= length < 120 or 160 < length <= 180:
                status, color, suggestion = 'acceptable', 'yellow', '长度基本可接受，可适当调整'
            else:
                status, color, suggestion = 'needs_improvement', 'red', '长度需要调整，建议在120-160字符之间'

            meta_desc_result = {
                'description': desc,
                'length': length,
                'status': status,
                'color': color,
                'suggestion': suggestion
            }

            # 处理标题优化
            title_opt = result.get('title_analysis', {})
            title_optimization = {
                'score': title_opt.get('score', 70),
                'current_title': title,
                'feedback': title_opt.get('feedback', '暂无评价'),
                'suggestions': title_opt.get('optimized_titles', [])
            }

            # 计算总体评分
            seo_score = cls._calculate_seo_score(
                keywords_with_density,
                title_optimization,
                meta_desc_result
            )

            return {
                'seo_score': seo_score,
                'keywords': keywords_with_density,
                'title_optimization': title_optimization,
                'meta_description': meta_desc_result,
                'internal_links': []  # 内链建议单独处理
            }

        except Exception as e:
            logger.error(f"统一SEO分析失败: {e}")
            return cls._get_default_result()

    @classmethod
    async def get_or_create_analysis(
        cls,
        content: str,
        title: str = "",
        user_id: Optional[int] = None,
        article_id: Optional[str] = None,
        force_refresh: bool = False
    ) -> Dict[str, Any]:
        """
        获取或创建SEO分析
        - 先检查数据库是否有结果
        - 如果没有或强制刷新，触发后台分析
        - 返回已有数据（可能稍旧），不等待新分析完成

        Args:
            content: 文章内容
            title: 文章标题
            user_id: 用户ID
            article_id: 文章ID
            force_refresh: 是否强制刷新

        Returns:
            SEO分析结果（可能来自缓存或实时）
        """
        cls.ensure_table_exists()

        # 1. 先查询数据库
        if article_id:
            existing = cls._get_from_db(article_id)
            if existing and not force_refresh:
                # 如果正在分析中，返回旧数据
                if existing.get('is_analyzing'):
                    logger.info(f"文章 {article_id} 正在分析中，返回旧数据")
                return existing

        # 2. 触发后台分析（不等待）
        if article_id and user_id:
            cls._trigger_background_analysis(
                content, title, user_id, article_id
            )

        # 3. 如果有旧数据，返回旧数据
        if article_id:
            existing = cls._get_from_db(article_id)
            if existing:
                return existing

        # 4. 如果没有数据，同步执行分析（首次）
        return await cls.analyze_and_save(
            content, title, user_id, article_id
        )

    @classmethod
    def _get_from_db(cls, article_id: str) -> Optional[Dict[str, Any]]:
        """从数据库获取SEO分析结果"""
        try:
            with Database.get_cursor() as cursor:
                cursor.execute("""
                    SELECT seo_score, keywords, title_optimization,
                           meta_description, internal_links, is_analyzing,
                           created_at, updated_at
                    FROM article_seo_analysis
                    WHERE article_id = %s
                """, (article_id,))
                row = cursor.fetchone()

                if row:
                    return {
                        'seo_score': row['seo_score'],
                        'keywords': row['keywords'],
                        'title_optimization': row['title_optimization'],
                        'meta_description': row['meta_description'],
                        'internal_links': row['internal_links'],
                        'is_analyzing': row['is_analyzing'],
                        'created_at': row['created_at'].isoformat() if row['created_at'] else None,
                        'updated_at': row['updated_at'].isoformat() if row['updated_at'] else None
                    }
        except Exception as e:
            logger.error(f"从数据库获取SEO分析失败: {e}")
        return None

    @classmethod
    async def analyze_and_save(
        cls,
        content: str,
        title: str = "",
        user_id: Optional[int] = None,
        article_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """执行分析并保存到数据库"""
        # 执行分析
        result = await cls.analyze_all_in_one(content, title, user_id, article_id)

        # 保存到数据库
        if article_id and user_id:
            cls._save_to_db(article_id, user_id, result)

        return result

    @classmethod
    def _save_to_db(cls, article_id: str, user_id: int, result: Dict[str, Any]):
        """保存分析结果到数据库"""
        try:
            with Database.get_cursor() as cursor:
                cursor.execute("""
                    INSERT INTO article_seo_analysis
                        (article_id, user_id, seo_score, keywords,
                         title_optimization, meta_description, internal_links,
                         is_analyzing, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
                    ON CONFLICT (article_id)
                    DO UPDATE SET
                        seo_score = EXCLUDED.seo_score,
                        keywords = EXCLUDED.keywords,
                        title_optimization = EXCLUDED.title_optimization,
                        meta_description = EXCLUDED.meta_description,
                        internal_links = EXCLUDED.internal_links,
                        is_analyzing = EXCLUDED.is_analyzing,
                        updated_at = NOW(),
                        analysis_version = article_seo_analysis.analysis_version + 1
                """, (
                    article_id,
                    user_id,
                    json.dumps(result['seo_score']),
                    json.dumps(result['keywords']),
                    json.dumps(result['title_optimization']),
                    json.dumps(result['meta_description']),
                    json.dumps(result.get('internal_links', [])),
                    False
                ))
                logger.info(f"SEO分析结果已保存: article_id={article_id}")
        except Exception as e:
            logger.error(f"保存SEO分析结果失败: {e}")

    @classmethod
    def _trigger_background_analysis(
        cls,
        content: str,
        title: str,
        user_id: int,
        article_id: str
    ):
        """触发后台分析任务"""
        try:
            # 标记为分析中
            with Database.get_cursor() as cursor:
                cursor.execute("""
                    INSERT INTO article_seo_analysis
                        (article_id, user_id, seo_score, keywords,
                         title_optimization, meta_description, is_analyzing)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (article_id)
                    DO UPDATE SET is_analyzing = TRUE, updated_at = NOW()
                """, (
                    article_id, user_id,
                    json.dumps({'score': 0, 'level': 'analyzing', 'feedback': ['分析中...']}),
                    json.dumps([]),
                    json.dumps({'suggestions': []}),
                    json.dumps({'description': ''}),
                    True
                ))

            # 使用 ARQ worker 进行后台分析
            # 这里简化处理，直接启动一个异步任务
            import asyncio
            asyncio.create_task(cls._background_analyze(
                content, title, user_id, article_id
            ))
            logger.info(f"后台SEO分析已触发: article_id={article_id}")
        except Exception as e:
            logger.error(f"触发后台分析失败: {e}")

    @classmethod
    async def _background_analyze(
        cls,
        content: str,
        title: str,
        user_id: int,
        article_id: str
    ):
        """后台执行分析"""
        try:
            result = await cls.analyze_all_in_one(content, title, user_id, article_id)
            cls._save_to_db(article_id, user_id, result)
            logger.info(f"后台SEO分析完成: article_id={article_id}")
        except Exception as e:
            logger.error(f"后台SEO分析失败: {e}")
            # 更新错误状态
            try:
                with Database.get_cursor() as cursor:
                    cursor.execute("""
                        UPDATE article_seo_analysis
                        SET is_analyzing = FALSE,
                            seo_score = %s,
                            updated_at = NOW()
                        WHERE article_id = %s
                    """, (
                        json.dumps({'score': 0, 'level': 'error', 'feedback': ['分析失败']}),
                        article_id
                    ))
            except Exception as inner_e:
                logger.error(f"更新错误状态失败: {inner_e}")

    @classmethod
    def calculate_keyword_density(cls, content: str, keyword: str) -> Dict[str, Any]:
        """计算关键词密度（纯规则，不调用LLM）"""
        if not content or not keyword:
            return {
                'keyword': keyword,
                'density': 0.0,
                'count': 0,
                'status': 'unknown',
                'suggestion': '无效输入'
            }

        content_lower = content.lower()
        keyword_lower = keyword.lower()

        # 统计关键词出现次数
        pattern = r'\b' + re.escape(keyword_lower) + r'\b'
        count = len(re.findall(pattern, content_lower))
        density = (count * len(keyword) / len(content)) * 100

        # 判断密度状态
        if cls.KEYWORD_DENSITY_TARGETS['good'][0] <= density <= cls.KEYWORD_DENSITY_TARGETS['good'][1]:
            status, color, suggestion = 'good', 'green', '密度适中，符合SEO最佳实践'
        elif cls.KEYWORD_DENSITY_TARGETS['acceptable'][0] <= density <= cls.KEYWORD_DENSITY_TARGETS['acceptable'][1]:
            status, color, suggestion = 'acceptable', 'yellow', '密度可接受，可适当调整'
        elif density < cls.KEYWORD_DENSITY_TARGETS['low'][1]:
            status, color, suggestion = 'low', 'red', '密度过低，建议增加关键词出现频率'
        else:
            status, color, suggestion = 'high', 'red', '密度过高，可能被视为关键词堆砌'

        return {
            'keyword': keyword,
            'density': round(density, 2),
            'count': count,
            'status': status,
            'color': color,
            'suggestion': suggestion
        }

    @classmethod
    def _calculate_seo_score(
        cls,
        keywords: List[Dict[str, Any]],
        title_opt: Dict[str, Any],
        meta_desc: Dict[str, Any]
    ) -> Dict[str, Any]:
        """计算总体SEO评分"""
        score = 0
        feedback = []

        # 关键词评分（40%权重）
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

        # 标题评分（35%权重）
        title_score = title_opt.get('score', 70)
        score += title_score * 0.35

        if title_score >= 85:
            feedback.append('标题SEO表现优秀')
        elif title_score >= 70:
            feedback.append('标题基本符合SEO要求')
        else:
            feedback.append('标题需要优化')

        # 元描述评分（25%权重）
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

        score = round(score)

        # 确定等级
        if score >= 85:
            level, level_label, color = 'excellent', '优秀 🌟', 'green'
        elif score >= 70:
            level, level_label, color = 'good', '良好 👍', 'blue'
        elif score >= 50:
            level, level_label, color = 'average', '一般 ⚖️', 'yellow'
        else:
            level, level_label, color = 'poor', '需改进 ⚠️', 'red'

        return {
            'score': score,
            'level': level,
            'level_label': level_label,
            'color': color,
            'feedback': feedback
        }

    @classmethod
    def _get_default_result(cls) -> Dict[str, Any]:
        """获取默认结果"""
        return {
            'seo_score': {
                'score': 0,
                'level': 'poor',
                'level_label': '需改进 ⚠️',
                'color': 'red',
                'feedback': ['内容过短，无法分析']
            },
            'keywords': [],
            'title_optimization': {
                'score': 0,
                'current_title': '',
                'feedback': '内容过短',
                'suggestions': []
            },
            'meta_description': {
                'description': '',
                'length': 0,
                'status': 'error',
                'color': 'red',
                'suggestion': '内容过短'
            },
            'internal_links': []
        }
