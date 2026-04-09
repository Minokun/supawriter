# -*- coding: utf-8 -*-
"""
热点服务
复用 page/hotspots.py 的爬虫逻辑
"""

import requests
import re
import json
import html
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from backend.api.core.redis_client import redis_client

logger = logging.getLogger(__name__)

CACHE_TTL = 300  # 5分钟缓存


class HotspotsService:
    """热点服务类"""
    
    def __init__(self):
        """初始化热点服务"""
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
    
    async def get_hotspots(self, source: str) -> Dict[str, Any]:
        """
        获取热点数据（带缓存）
        
        Args:
            source: 热点来源 (baidu/weibo/douyin/thepaper/36kr)
            
        Returns:
            热点数据字典
        """
        # 先从 Redis 缓存获取
        cached_data = await redis_client.get_cached_hotspots(source)
        if cached_data:
            logger.info(f"从缓存获取热点数据: {source}")
            return {"success": True, "data": cached_data, "from_cache": True}
        
        # 缓存未命中，爬取数据
        logger.info(f"爬取热点数据: {source}")
        
        if source == 'baidu':
            result = await self._get_baidu_data()
        elif source == 'weibo':
            result = await self._get_weibo_data()
        elif source == 'douyin':
            result = await self._get_douyin_data()
        elif source == 'thepaper':
            result = await self._get_thepaper_data()
        elif source == '36kr':
            result = await self._get_36kr_data()
        else:
            return {"success": False, "error": "不支持的热点源"}
        
        # 缓存数据
        if result.get('success'):
            await redis_client.cache_hotspots(source, result['data'], CACHE_TTL)
        
        result['from_cache'] = False
        return result
    
    async def _get_baidu_data(self) -> Dict[str, Any]:
        """获取百度热搜数据"""
        try:
            url = "https://top.baidu.com/board?tab=realtime"
            response = requests.get(url, headers=self.headers, timeout=10)
            json_match = re.search(r'<!--s-data:({.*?})-->', response.text)
            if json_match:
                data = json.loads(json_match.group(1))
                cards = data.get('data', {}).get('cards', [])
                if cards:
                    content = cards[0].get('content', [])
                    result = []
                    for item in content:
                        result.append({
                            'title': item.get('word', ''),
                            'desc': item.get('desc', ''),
                            'url': item.get('url', '') or f"https://www.baidu.com/s?wd={item.get('word', '')}",
                            'hot_score': item.get('hotScore', '')
                        })
                    return {'success': True, 'data': result}
        except Exception as e:
            logger.error(f"获取百度热搜失败: {e}")
        return {'success': False, 'error': '获取数据失败'}
    
    async def _get_weibo_data(self) -> Dict[str, Any]:
        """获取微博热搜数据"""
        try:
            url = "https://s.weibo.com/top/summary"
            headers = {
                **self.headers,
                'Cookie': 'SUB=_2AkMWJ_fdf8NxqwJRmP8SxWjnaY12yQ_EieKkjrMJJRMxHRl-yT9jqmgbtRB6PO6Nc9vS-pTH2Q7q8lW1D4q4e6P4'
            }
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                items = re.findall(r'<a href="(/weibo\?q=[^"]+)"[^>]*>(.*?)</a>.*?<span[^>]*>(.*?)</span>', response.text, re.DOTALL)
                if not items:
                    items = re.findall(r'<a href="(/weibo\?q=[^"]+)"[^>]*>(.*?)</a>', response.text)
                    items = [(x[0], x[1], "") for x in items]
                
                hot_list = []
                seen_titles = set()
                for link, title, heat in items:
                    title = html.unescape(title).strip()
                    heat = heat.strip()
                    if title in ['首页', '发现', '游戏', '注册', '登录', '帮助']:
                        continue
                    if title not in seen_titles:
                        seen_titles.add(title)
                        hot_list.append({
                            'title': title,
                            'url': f"https://s.weibo.com{link}",
                            'heat': heat
                        })
                return {'success': True, 'data': hot_list[:30]}
        except Exception as e:
            logger.error(f"获取微博热搜失败: {e}")
        return {'success': False, 'error': '获取数据失败'}
    
    async def _get_douyin_data(self) -> Dict[str, Any]:
        """获取抖音热搜数据"""
        try:
            url = "https://www.douyin.com/aweme/v1/web/hot/search/list/"
            headers = {
                **self.headers,
                'Referer': 'https://www.douyin.com/billboard/',
            }
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                word_list = data.get('data', {}).get('word_list', [])
                result = []
                for item in word_list:
                    result.append({
                        'title': item.get('word', ''),
                        'hot_value': item.get('hot_value', 0),
                        'url': f"https://www.douyin.com/search/{item.get('word', '')}"
                    })
                return {'success': True, 'data': result}
        except Exception as e:
            logger.error(f"获取抖音热搜失败: {e}")
        return {'success': False, 'error': '获取数据失败'}
    
    async def _get_thepaper_data(self) -> Dict[str, Any]:
        """获取澎湃新闻数据"""
        try:
            url = "https://cache.thepaper.cn/contentapi/wwwIndex/rightSidebar"
            headers = {
                **self.headers,
                'Accept': 'application/json, text/plain, */*',
                'Referer': 'https://www.thepaper.cn/',
            }
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code == 200:
                data = response.json()
                return {'success': True, 'data': data.get('data', {}).get('hotNews', [])}
        except Exception as e:
            logger.error(f"获取澎湃新闻失败: {e}")
        return {'success': False, 'error': '获取数据失败'}
    
    async def _get_36kr_data(self) -> Dict[str, Any]:
        """获取36Kr数据"""
        try:
            # 方案1: 今日热榜
            tophub_url = "https://tophub.today/n/Q1Vd5Ko85R"
            response = requests.get(tophub_url, headers=self.headers, timeout=15)
            if response.status_code == 200 and '安全验证' not in response.text:
                pattern = r'<td[^>]*>(\d+)\.</td>\s*<td[^>]*>\s*<a[^>]*href="([^"]+)"[^>]*>([^<]+)</a>\s*</td>\s*<td[^>]*class="ws"[^>]*>([^<]*)</td>'
                items = re.findall(pattern, response.text)
                if items:
                    result = []
                    for rank, item_url, title, hot in items[:20]:
                        result.append({
                            'title': html.unescape(title.strip()),
                            'url': item_url,
                            'hot': hot.strip()
                        })
                    return {'success': True, 'data': result, 'source': 'tophub'}
            
            # 方案2: 36Kr官网
            url = "https://36kr.com/newsflashes"
            response = requests.get(url, headers=self.headers, timeout=10)
            if response.status_code == 200:
                links = re.findall(r'href="/newsflashes/(\d+)"[^>]*>([^<]+)</a>', response.text)
                if links:
                    result = []
                    for item_id, title in links[:20]:
                        title = html.unescape(title.strip())
                        if title and len(title) > 5:
                            result.append({
                                'title': title,
                                'url': f"https://36kr.com/newsflashes/{item_id}",
                                'hot': ''
                            })
                    return {'success': True, 'data': result, 'source': '36kr'}
        except Exception as e:
            logger.error(f"获取36Kr数据失败: {e}")
        return {'success': False, 'error': '获取数据失败'}


# 全局实例
hotspots_service = HotspotsService()
