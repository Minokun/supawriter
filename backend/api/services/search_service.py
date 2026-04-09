# -*- coding: utf-8 -*-
"""
Search Service - 网络搜索服务
提供统一的搜索接口，支持智能搜索判断、Redis 缓存、DDGS 搜索
"""

import hashlib
import json
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any

from backend.api.core.redis_client import redis_client


logger = logging.getLogger(__name__)


class SearchService:
    """
    网络搜索服务

    提供智能搜索判断、搜索执行、缓存管理等功能
    """

    # TTL 设置：300 秒（5 分钟）
    CACHE_TTL = 300

    def __init__(self, user_id: Optional[int] = None):
        """
        初始化搜索服务

        Args:
            user_id: 用户 ID，用于缓存键生成
        """
        self.user_id = user_id

    def _get_cache_key(self, query: str) -> str:
        """
        生成缓存键

        格式: search:{user_id}:{query_hash}
        query_hash 为 query 的 md5 值

        Args:
            query: 搜索查询

        Returns:
            缓存键字符串
        """
        query_hash = hashlib.md5(query.encode('utf-8')).hexdigest()
        user_prefix = self.user_id if self.user_id is not None else 'default'
        return f"search:{user_prefix}:{query_hash}"

    def should_search(self, query: str, user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        调用 LLM 判断是否需要搜索

        Args:
            query: 用户查询
            user_id: 用户 ID（可选，用于获取用户配置的模型）

        Returns:
            {
                'need_search': bool,  # 是否需要搜索
                'optimized_query': str,  # 优化后的查询（可选）
                'reason': str  # 判断原因
            }
        """
        # 首先检查是否包含2026年之后的年份或时间词（LLM知识截止日期之后的）
        import re

        # 匹配 2026-2029 年份
        year_pattern = r'20[2-9][0-9]'
        years_in_query = re.findall(year_pattern, query, re.IGNORECASE)

        # 检查未来年份
        future_years = [y for y in years_in_query if int(y) >= 2026]

        # 检查2026之后的时间相关词汇
        time_keywords_future = ['2026', '2027', '2028', '2029', '2030', '今年', '本月', '最近', '现在', '当前']

        query_lower = query.lower()
        has_future_time = any(keyword.lower() in query_lower for keyword in time_keywords_future)

        # 如果包含未来年份或时间词，强制搜索（因为LLM知识只到2025年）
        if future_years or has_future_time:
            reason_parts = []
            if future_years:
                reason_parts.append(f"查询包含未来年份 {', '.join(future_years)}")
            if has_future_time:
                reason_parts.append("查询包含当前/最近时间词")
            reason = f"{'，'.join(reason_parts)}（LLM知识截止于2025年，需要搜索最新信息）"

            return {
                'need_search': True,
                'optimized_query': query,
                'reason': reason
            }

        # 搜索判断 Prompt
        SEARCH_JUDGMENT_PROMPT = """分析用户问题，判断是否需要进行网络搜索，并优化搜索查询词。

用户问题: {query}

返回JSON格式：
{{
  "need_search": true/false,
  "optimized_query": "优化后的查询词 (need_search为false时为空字符串)",
  "reason": "判断原因"
}}

判断标准：
- 问题涉及具体事实、最新信息、特定技术时 → need_search: true
- 问题涉及实时数据、新闻、价格等 → need_search: true
- 问题要求准确数据、具体参数、技术细节 → need_search: true
- 基于已有对话可以回答的简单对话 → need_search: false
- 重复问题或追问时 → need_search: false

**重要提示**：当前时间是2026年，LLM训练数据只到2025年。如果用户询问2026年或之后的事情，必须搜索。

查询词优化规则：
- 提取核心关键词和概念，去除无关停用词
- 保留专业术语、品牌名称、技术名词的完整性
- 关键词之间使用空格分隔
- 保留年份、版本号等重要限定词

只返回JSON，不要其他解释。"""

        try:
            # 添加项目根目录到路径
            backend_root = Path(__file__).parent.parent.parent
            if str(backend_root) not in sys.path:
                sys.path.insert(0, str(backend_root))

            from utils.llm_chat import chat

            # 调用 LLM 进行搜索判断
            system_prompt = SEARCH_JUDGMENT_PROMPT.replace('{query}', query)

            logger.info(f"调用 LLM 判断是否需要搜索: {query}")

            response = chat(
                prompt="请分析用户问题并判断是否需要搜索。",
                system_prompt=system_prompt,
                max_tokens=500
            )

            logger.info(f"LLM 搜索判断响应: {response}")

            # 解析 LLM 返回的 JSON
            # 尝试从响应中提取 JSON
            import re
            json_match = re.search(r'\{[^}]*\}', response)

            if json_match:
                result = json.loads(json_match.group())

                # 验证返回的字段
                need_search = result.get('need_search', False)
                optimized_query = result.get('optimized_query', query) if need_search else ''
                reason = result.get('reason', '基于LLM判断的结果')

                return {
                    'need_search': need_search,
                    'optimized_query': optimized_query,
                    'reason': reason
                }
            else:
                # 如果无法解析 JSON，使用保守策略：默认搜索
                logger.warning(f"LLM 返回无法解析的 JSON: {response}，使用保守策略")
                return {
                    'need_search': True,
                    'optimized_query': query,
                    'reason': 'LLM 返回格式异常，使用保守策略进行搜索'
                }

        except Exception as e:
            logger.error(f"LLM 搜索判断失败: {e}，使用保守策略")
            # 失败时使用保守策略：默认搜索
            return {
                'need_search': True,
                'optimized_query': query,
                'reason': f'LLM 判断失败({str(e)})，使用保守策略'
            }

    def execute_search(
        self,
        query: str,
        max_results: int = 10,
        force_search: bool = False
    ) -> Dict[str, Any]:
        """
        执行搜索

        执行流程：
        1. 检查 Redis 缓存
        2. 如果缓存未命中，执行 DDGS 搜索
        3. LLM 筛选和格式化结果
        4. 写入缓存

        Args:
            query: 搜索查询
            max_results: 最大结果数量
            force_search: 强制搜索（忽略缓存）

        Returns:
            {
                'optimized_query': str,
                'sources': [
                    {'title': str, 'url': str, 'snippet': str},
                    ...
                ]
            }
        """
        cache_key = self._get_cache_key(query)

        # 1. 检查缓存（除非强制搜索）
        if not force_search:
            try:
                cached = redis_client.sync_client.get(cache_key)
                if cached:
                    logger.info(f"搜索缓存命中: {cache_key}")
                    return json.loads(cached)
            except Exception as e:
                logger.warning(f"读取搜索缓存失败: {e}")

        # 2. 执行 DDGS 搜索
        try:
            # 添加项目根目录到路径
            backend_root = Path(__file__).parent.parent.parent.parent
            if str(backend_root) not in sys.path:
                sys.path.insert(0, str(backend_root))

            from utils.ddgs_utils import search_ddgs

            logger.info(f"开始 DDGS 搜索: {query}")
            raw_results = search_ddgs(
                query=query,
                search_type="text",
                max_results=max_results
            )

            # 3. 格式化搜索结果并使用 LLM 筛选
            logger.info(f"DDGS 搜索完成，获取 {len(raw_results)} 条原始结果")

            # 构建搜索结果列表用于 LLM 筛选
            search_results_for_filtering = []
            for r in raw_results:
                search_results_for_filtering.append({
                    'title': r.get("title", ""),
                    'url': r.get("href", ""),
                    'snippet': r.get("body", ""),
                    'source': r.get("source", "")
                })

            # 3.1 如果有搜索结果，使用 LLM 筛选
            filtered_sources = []
            if search_results_for_filtering:
                try:
                    from utils.llm_chat import chat

                    # LLM 筛选 Prompt
                    FILTERING_PROMPT = """你是一个搜索结果筛选器。分析以下搜索结果，只保留与用户问题**高度相关**的结果。

用户问题: {query}

搜索结果:
{search_results_json}

判断标准：
- 结果内容必须与用户问题直接相关
- 优先保留来自权威来源（如官方文档、知名网站）
- 过滤掉明显不相关的内容
- 过滤掉广告或低质量内容

返回JSON格式：
{{
  "relevant_indices": [0, 2, 4],  // 相关结果的索引数组
  "reason": "筛选原因"
}}

只返回JSON，不要其他解释。"""

                    # 将搜索结果格式化为 JSON 字符串
                    import json
                    search_results_json = json.dumps(search_results_for_filtering, ensure_ascii=False, indent=2)

                    filtering_system_prompt = FILTERING_PROMPT.replace('{query}', query).replace('{search_results_json}', search_results_json)

                    logger.info(f"开始 LLM 筛选搜索结果...")

                    filter_response = chat(
                        prompt="请筛选搜索结果，只保留相关的结果。",
                        system_prompt=filtering_system_prompt,
                        max_tokens=1000
                    )

                    logger.info(f"LLM 筛选响应: {filter_response}")

                    # 解析 LLM 返回的索引
                    filter_json_match = re.search(r'\{[^}]*\}', filter_response)
                    if filter_json_match:
                        filter_result = json.loads(filter_json_match.group())
                        relevant_indices = filter_result.get('relevant_indices', [])

                        # 只保留相关的结果
                        for idx in relevant_indices:
                            if 0 <= idx < len(search_results_for_filtering):
                                filtered_sources.append(search_results_for_filtering[idx])

                        logger.info(f"LLM 筛选完成，保留 {len(filtered_sources)} 条相关结果，原因为: {filter_result.get('reason', 'N/A')}")
                    else:
                        # 如果无法解析，保留所有结果
                        logger.warning(f"LLM 筛选返回格式异常，保留所有结果")
                        filtered_sources = search_results_for_filtering

                except Exception as e:
                    logger.error(f"LLM 筛选失败: {e}，保留所有结果")
                    filtered_sources = search_results_for_filtering
            else:
                # 没有搜索结果
                filtered_sources = []

            sources = filtered_sources[:max_results]

            # 4. 构建结果
            result = {
                'optimized_query': query,
                'sources': sources
            }

            # 5. 写入缓存
            try:
                redis_client.sync_client.setex(
                    cache_key,
                    self.CACHE_TTL,
                    json.dumps(result, ensure_ascii=False)
                )
                logger.info(f"搜索结果已缓存: {cache_key}")
            except Exception as e:
                logger.warning(f"写入搜索缓存失败: {e}")

            return result

        except RuntimeError as e:
            logger.error(f"DDGS 搜索失败: {e}")
            # 返回空结果，但不抛出异常
            return {
                'optimized_query': query,
                'sources': []
            }
        except Exception as e:
            logger.error(f"搜索执行失败: {e}", exc_info=True)
            # 返回空结果，但不抛出异常
            return {
                'optimized_query': query,
                'sources': []
            }

    def invalidate_cache(self, query: Optional[str] = None):
        """
        失效缓存

        Args:
            query: 指定查询的缓存，如果为 None 则失效所有该用户的缓存
        """
        try:
            if query:
                # 失效指定查询的缓存
                cache_key = self._get_cache_key(query)
                redis_client.sync_client.delete(cache_key)
                logger.info(f"已失效搜索缓存: {cache_key}")
            else:
                # 失效该用户的所有搜索缓存
                user_prefix = self.user_id if self.user_id is not None else 'default'
                pattern = f"search:{user_prefix}:*"

                # 使用 SCAN 遍历并删除
                cursor = 0
                while True:
                    cursor, keys = redis_client.sync_client.scan(
                        cursor=cursor,
                        match=pattern,
                        count=100
                    )
                    if keys:
                        redis_client.sync_client.delete(*keys)
                        logger.info(f"已失效 {len(keys)} 个搜索缓存")
                    if cursor == 0:
                        break
        except Exception as e:
            logger.warning(f"失效缓存失败: {e}")


# 全局服务实例缓存
_service_cache: Dict[int, SearchService] = {}


def get_search_service(user_id: Optional[int] = None) -> SearchService:
    """
    获取搜索服务实例（带缓存）

    Args:
        user_id: 用户 ID

    Returns:
        SearchService 实例
    """
    cache_key = user_id if user_id is not None else 0

    if cache_key not in _service_cache:
        _service_cache[cache_key] = SearchService(user_id=user_id)

    return _service_cache[cache_key]


def clear_service_cache():
    """清除所有服务实例缓存"""
    global _service_cache
    _service_cache.clear()
