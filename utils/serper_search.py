# -*- coding: utf-8 -*-
"""
Serper 搜索引擎 API 封装
使用 Google Serper API 进行网络搜索
"""

import http.client
import json
import logging
import ssl
from typing import List, Dict, Optional

# 配置日志
logger = logging.getLogger(__name__)


class SerperSearch:
    """Serper 搜索引擎封装类"""
    
    def __init__(self, api_key: str):
        """
        初始化 Serper 搜索引擎
        
        Args:
            api_key: Serper API Key
        """
        self.api_key = api_key
        self.host = "google.serper.dev"
        
    def search(self, query: str, gl: str = "cn", hl: str = "zh-cn", 
               time_range: str = "y") -> Optional[Dict]:
        """
        执行搜索（注意：Serper API 固定返回约 10 条结果）
        
        Args:
            query: 搜索查询词
            gl: 国家/地区代码，默认"cn"（中国）
            hl: 语言代码，默认"zh-cn"（简体中文）
            time_range: 时间范围，默认"y"（一年内）
                       可选值：h(小时), d(天), w(周), m(月), y(年)
        
        Returns:
            搜索结果 JSON 数据，约 10 条结果，失败返回 None
        """
        try:
            # 创建不验证 SSL 证书的上下文
            context = ssl._create_unverified_context()
            conn = http.client.HTTPSConnection(self.host, context=context)
            
            # 构建请求数据（注意：不包含 num 参数，API 固定返回约 10 条）
            payload = json.dumps({
                "q": query,
                "gl": gl,
                "hl": hl,
                "tbs": f"qdr:{time_range}"
            })
            
            # 设置请求头
            headers = {
                'X-API-KEY': self.api_key,
                'Content-Type': 'application/json'
            }
            
            # 发送请求
            conn.request("POST", "/search", payload, headers)
            res = conn.getresponse()
            data = res.read()
            
            # 解析响应
            result = json.loads(data.decode("utf-8"))
            
            logger.info(f"Serper 搜索成功: query='{query}', 结果数={len(result.get('organic', []))}")
            return result
            
        except Exception as e:
            logger.error(f"Serper 搜索失败: {e}")
            return None
        finally:
            if 'conn' in locals():
                conn.close()
    
    def get_formatted_results(self, query: str, gl: str = "cn", 
                             hl: str = "zh-cn", time_range: str = "y") -> List[Dict]:
        """
        获取格式化的搜索结果（固定返回约 10 条）
        
        Args:
            query: 搜索查询词
            gl: 国家/地区代码
            hl: 语言代码
            time_range: 时间范围
        
        Returns:
            格式化后的搜索结果列表，约 10 条结果
        """
        raw_results = self.search(query, gl, hl, time_range)
        
        if not raw_results or 'organic' not in raw_results:
            logger.warning("Serper 搜索无结果或返回数据格式错误")
            return []
        
        formatted_results = []
        organic_results = raw_results.get('organic', [])
        
        for item in organic_results:
            # 转换为统一格式
            formatted_item = {
                'title': item.get('title', ''),
                'url': item.get('link', ''),
                'content': item.get('snippet', ''),
                # Serper 按 position 排序，position 越小越相关，转换为分数(1.0 - 0.5)
                'score': 1.0 - (item.get('position', 1) - 1) * 0.05,
                'source': 'serper',  # 标记来源
                'date': item.get('date', '')
            }
            formatted_results.append(formatted_item)
        
        logger.info(f"Serper 格式化结果: 原始 {len(organic_results)} 条 -> 格式化 {len(formatted_results)} 条")
        return formatted_results


def serper_search(api_key: str, query: str, gl: str = "cn", 
                  hl: str = "zh-cn", time_range: str = "y") -> List[Dict]:
    """
    便捷函数：执行 Serper 搜索并返回格式化结果（固定约 10 条）
    
    Args:
        api_key: Serper API Key
        query: 搜索查询词
        gl: 国家/地区代码
        hl: 语言代码
        time_range: 时间范围
    
    Returns:
        格式化后的搜索结果列表，约 10 条
    """
    # 验证 API key
    if not api_key or not isinstance(api_key, str) or api_key.strip() == '':
        logger.error("Serper API Key 无效或为空，无法执行搜索")
        return []
    
    searcher = SerperSearch(api_key)
    return searcher.get_formatted_results(query, gl, hl, time_range)
