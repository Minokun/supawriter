# -*- coding: utf-8 -*-
"""
Topic Selector Service
智能选题服务 - 从新闻源和热点获取数据，通过LLM按主题筛选并排序

复用 tweet_topics 路由中的智能选题逻辑，供 Agent Worker 调用
"""

import logging
import json
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

from utils.llm_chat import chat
import utils.prompt_template as pt

logger = logging.getLogger(__name__)


@dataclass
class RankedTopic:
    """排序后的选题结果"""
    title: str
    source: str = ''
    source_url: str = ''
    heat: int = 0
    relevance_score: int = 0  # 0-100 主题相关性
    value_score: int = 0  # 0-100 综合价值
    angle: str = ''  # 推荐切入角度
    reason: str = ''  # 推荐理由
    keywords: List[str] = field(default_factory=list)


class TopicSelector:
    """智能选题服务"""

    # 支持的新闻API源
    NEWS_API_SOURCES = ['澎湃科技', 'SOTA开源项目', '实时新闻', '新浪直播']

    # 支持的热点源
    HOTSPOT_SOURCES = ['baidu', 'weibo', 'douyin', 'thepaper', '36kr']

    async def select_topics(
        self,
        theme: str,
        theme_desc: Optional[str] = None,
        news_sources: Optional[List[str]] = None,
        hotspot_sources: Optional[List[str]] = None,
        max_topics: int = 3,
        model_type: str = 'deepseek',
        model_name: str = 'deepseek-chat',
    ) -> List[RankedTopic]:
        """
        智能选题：获取新闻/热点 → LLM按主题筛选 → 价值排序 → 返回Top N

        Args:
            theme: 主题名称
            theme_desc: 主题描述（可选，增强筛选精度）
            news_sources: 新闻API源列表（如 ["澎湃科技", "实时新闻"]）
            hotspot_sources: 热点源列表（如 ["baidu", "weibo"]）
            max_topics: 最多返回几个选题
            model_type: LLM provider
            model_name: LLM model name

        Returns:
            排序后的选题列表
        """
        logger.info(f"开始智能选题: theme={theme}, max_topics={max_topics}")

        # 1. 收集新闻和热点数据
        all_items = []

        if news_sources:
            news_items = self._fetch_news(news_sources)
            all_items.extend(news_items)
            logger.info(f"从新闻源获取到 {len(news_items)} 条新闻")

        if hotspot_sources:
            hotspot_items = await self._fetch_hotspots(hotspot_sources)
            all_items.extend(hotspot_items)
            logger.info(f"从热点源获取到 {len(hotspot_items)} 条热点")

        if not all_items:
            logger.warning("未获取到任何新闻或热点数据")
            return []

        logger.info(f"总共收集到 {len(all_items)} 条数据")

        # 2. 调用LLM进行智能筛选和排序
        ranked_topics = self._llm_rank_topics(
            theme=theme,
            theme_desc=theme_desc,
            items=all_items,
            max_topics=max_topics,
            model_type=model_type,
            model_name=model_name,
        )

        logger.info(f"智能选题完成，获得 {len(ranked_topics)} 个排序选题")
        return ranked_topics

    def _fetch_news(self, sources: List[str]) -> List[Dict[str, Any]]:
        """从新闻API源获取新闻"""
        from backend.api.routes.tweet_topics import fetch_news_by_source

        all_news = []
        for source in sources:
            if source not in self.NEWS_API_SOURCES:
                logger.warning(f"不支持的新闻源: {source}")
                continue
            try:
                news = fetch_news_by_source(source, 15)
                for item in news:
                    item['source'] = source
                    item['item_type'] = 'news'
                all_news.extend(news)
            except Exception as e:
                logger.error(f"获取 {source} 新闻失败: {e}")
        return all_news

    async def _fetch_hotspots(self, sources: List[str]) -> List[Dict[str, Any]]:
        """从热点源获取热搜数据"""
        from backend.api.services.hotspots_service import hotspots_service

        all_hotspots = []
        for source in sources:
            if source not in self.HOTSPOT_SOURCES:
                logger.warning(f"不支持的热点源: {source}")
                continue
            try:
                result = await hotspots_service.get_hotspots(source)
                if result.get('success'):
                    hotspots = result.get('data', [])
                    for item in hotspots:
                        if isinstance(item, dict):
                            item['source'] = source
                            item['item_type'] = 'hotspot'
                            if 'title' not in item and 'word' in item:
                                item['title'] = item['word']
                    all_hotspots.extend(hotspots)
            except Exception as e:
                logger.error(f"获取 {source} 热点失败: {e}")
        return all_hotspots

    def _format_items_for_prompt(self, items: List[Dict[str, Any]]) -> str:
        """格式化新闻/热点为LLM prompt"""
        formatted = []
        for idx, item in enumerate(items, 1):
            title = item.get('title', '') or item.get('word', '') or '无标题'
            summary = item.get('summary', '') or item.get('description', '') or ''
            source = item.get('source', '')
            url = item.get('url', '')
            heat = item.get('heat', '') or item.get('hot_score', '') or ''
            item_type = '热点' if item.get('item_type') == 'hotspot' else '新闻'

            text = f"【{item_type}{idx}】\n标题：{title}\n来源：{source}"
            if heat:
                text += f"\n热度：{heat}"
            if summary:
                text += f"\n内容：{summary}"
            if url:
                text += f"\n链接：{url}"
            text += "\n---"
            formatted.append(text)

        return "\n\n".join(formatted)

    def _llm_rank_topics(
        self,
        theme: str,
        theme_desc: Optional[str],
        items: List[Dict[str, Any]],
        max_topics: int,
        model_type: str,
        model_name: str,
    ) -> List[RankedTopic]:
        """调用LLM进行智能筛选和排序"""
        items_content = self._format_items_for_prompt(items)

        theme_info = theme
        if theme_desc:
            theme_info += f"（{theme_desc}）"

        prompt = f"""用户关注的主题是：{theme_info}

以下是从多个来源获取的新闻和热点：

<content>
{items_content}
</content>

请执行以下任务：
1. 筛选出与主题"{theme}"最相关的内容（最多20条）
2. 从筛选后的内容中，选出最有价值的 {max_topics} 个选题方向
3. 对每个选题进行价值评估，考虑以下维度：
   - relevance_score (0-100): 与主题的相关程度
   - value_score (0-100): 综合价值（考虑热度、原创性、时效性、传播潜力）
4. 按 relevance_score * 0.6 + value_score * 0.4 的综合得分从高到低排序

严格返回以下JSON格式（不要添加任何其他内容）：
```json
{{
  "topics": [
    {{
      "title": "选题标题",
      "source_news_title": "来源新闻/热点的原始标题",
      "source": "来源平台",
      "relevance_score": 85,
      "value_score": 90,
      "angle": "推荐的切入角度",
      "reason": "推荐理由（50字以内）",
      "keywords": ["关键词1", "关键词2"]
    }}
  ],
  "summary": "本次选题整体总结（100字以内）"
}}
```"""

        try:
            response = chat(
                prompt=prompt,
                system_prompt=pt.TWEET_TOPIC_GENERATOR,
                model_type=model_type,
                model_name=model_name,
                max_tokens=16384,
            )
        except Exception as e:
            logger.error(f"LLM智能选题调用失败: {e}", exc_info=True)
            return []

        # 解析LLM响应
        topics_data = self._parse_llm_response(response)
        if not topics_data or not topics_data.get('topics'):
            logger.error("LLM智能选题响应解析失败")
            return []

        # 转换为RankedTopic并匹配URL
        ranked = []
        title_to_item = self._build_title_index(items)

        for topic in topics_data['topics'][:max_topics]:
            source_title = topic.get('source_news_title', '')
            matched_item = self._match_source_item(source_title, title_to_item)

            ranked.append(RankedTopic(
                title=topic.get('title', ''),
                source=topic.get('source', matched_item.get('source', '') if matched_item else ''),
                source_url=matched_item.get('url', '') if matched_item else '',
                heat=matched_item.get('heat', 0) or matched_item.get('hot_score', 0) if matched_item else 0,
                relevance_score=topic.get('relevance_score', 0),
                value_score=topic.get('value_score', 0),
                angle=topic.get('angle', ''),
                reason=topic.get('reason', ''),
                keywords=topic.get('keywords', []),
            ))

        # 按综合得分排序
        ranked.sort(key=lambda t: t.relevance_score * 0.6 + t.value_score * 0.4, reverse=True)

        return ranked

    def _build_title_index(self, items: List[Dict[str, Any]]) -> Dict[str, Dict]:
        """构建标题索引用于匹配"""
        index = {}
        for item in items:
            title = item.get('title', '') or item.get('word', '')
            if title:
                index[title[:30]] = item
        return index

    def _match_source_item(
        self,
        source_title: str,
        title_index: Dict[str, Dict]
    ) -> Optional[Dict]:
        """模糊匹配源内容"""
        if not source_title:
            return None

        source_key = source_title[:30]

        # 精确匹配
        if source_key in title_index:
            return title_index[source_key]

        # 模糊匹配
        for key, item in title_index.items():
            if source_key in key or key in source_key:
                return item

        return None

    def _parse_llm_response(self, response: str) -> Optional[Dict[str, Any]]:
        """解析LLM响应为JSON（复用tweet_topics的解析逻辑）"""
        from backend.api.routes.tweet_topics import parse_llm_response
        return parse_llm_response(response)


# 全局实例
topic_selector = TopicSelector()
