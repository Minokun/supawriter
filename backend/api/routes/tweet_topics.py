# -*- coding: utf-8 -*-
"""推文选题 API 路由"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any, Dict, List, Optional
import logging
import json
import re
import requests

from backend.api.core.dependencies import get_current_user, get_db
from backend.api.repositories.user_topics import UserTopicsRepository
from utils.database import Database
from utils.llm_chat import chat, _get_db_llm_providers
import utils.prompt_template as pt
from utils.history_utils import (
    add_tweet_topics_record,
    load_tweet_topics_history,
    delete_tweet_topics_record,
)

logger = logging.getLogger(__name__)
router = APIRouter()


def _resolve_writer_model(current_user_id: int) -> tuple[str, str]:
    with Database.get_cursor() as cursor:
        cursor.execute(
            """
            SELECT writer_model FROM user_model_configs WHERE user_id = %s
            """,
            (current_user_id,),
        )
        model_row = cursor.fetchone()
        writer_model = model_row['writer_model'] if model_row else 'deepseek:deepseek-chat'

    if ':' in writer_model:
        return writer_model.split(':', 1)

    return 'deepseek', writer_model


def _ensure_writer_provider_ready(model_type: str) -> None:
    providers = _get_db_llm_providers()

    if not providers:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail='没有可用的 LLM 提供商配置，请先在系统设置中配置',
        )

    provider = providers.get(model_type)
    if not provider or not provider.get('api_key'):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f'提供商 {model_type} 不存在，请在系统设置中配置',
        )


class TweetTopicsGenerateRequest(BaseModel):
    news_source: str = Field('澎湃科技', description='新闻源')
    news_count: int = Field(15, ge=5, le=30, description='新闻数量')
    topic_count: int = Field(8, ge=3, le=15, description='选题数量')


class TweetTopicsGenerateResponse(BaseModel):
    record_id: int
    mode: str
    topic_name: Optional[str] = None
    news_source: str
    news_count: int
    topics_data: Dict[str, Any]
    model_type: str
    model_name: str
    news_urls: List[str] = Field(default_factory=list)


class IntelligentGenerateRequest(BaseModel):
    topic_id: Optional[int] = Field(None, description='已保存主题ID')
    custom_topic: Optional[str] = Field(None, description='自定义主题')
    save_topic: bool = Field(False, description='是否保存自定义主题')
    topic_description: Optional[str] = Field(None, description='主题描述')
    topic_count: int = Field(10, ge=3, le=10, description='选题数量')


class IntelligentGenerateResponse(BaseModel):
    record_id: int
    mode: str
    topic_name: Optional[str]
    news_source: str
    news_count: int
    topics_data: Dict[str, Any]
    model_type: str
    model_name: str


class CreateTopicRequest(BaseModel):
    topic_name: str = Field(..., description='主题名称')
    description: Optional[str] = Field(None, description='主题描述')


@router.post('/generate', response_model=TweetTopicsGenerateResponse)
async def generate_tweet_topics(
    request_data: TweetTopicsGenerateRequest,
    current_user_id: int = Depends(get_current_user),
):
    """生成推文选题"""
    # 获取用户信息
    with Database.get_cursor() as cursor:
        cursor.execute("SELECT username FROM users WHERE id = %s", (current_user_id,))
        user_row = cursor.fetchone()
        username = user_row['username'] if user_row else f"user_{current_user_id}"

    model_type, model_name = _resolve_writer_model(current_user_id)
    _ensure_writer_provider_ready(model_type)

    # 获取新闻
    news_data = fetch_news_by_source(request_data.news_source, request_data.news_count)
    if not news_data:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail='获取新闻失败或无内容',
        )

    # 提取新闻 URL（如果有）
    news_urls = [news.get('url', '') for news in news_data if news.get('url')]

    news_content = format_news_for_prompt(news_data)
    prompt = f"""<news_content>
{news_content}
</news_content>

请基于以上新闻内容，生成 {request_data.topic_count} 个优质的公众号推文选题。

返回JSON格式，包含以下字段：
- topics: 选题列表
- summary: 整体总结
- hot_keywords: 热门关键词列表

不要添加任何其他内容。"""

    try:
        response = chat(
            prompt=prompt,
            system_prompt=pt.TWEET_TOPIC_GENERATOR,
            model_type=model_type,
            model_name=model_name,
            max_tokens=16384,
        )
    except Exception as exc:
        logger.error(f"生成推文选题失败: {exc}", exc_info=True)
        if '提供商' in str(exc) or 'API Key' in str(exc):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(exc),
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='生成推文选题失败',
        ) from exc

    topics_data = parse_llm_response(response)
    if not topics_data or not topics_data.get('topics'):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='未能解析模型输出，请重试',
        )

    # 为每个topic匹配对应的URL
    topics_data = match_urls_to_topics(news_data, topics_data)

    record = add_tweet_topics_record(
        username=username,
        news_source=request_data.news_source,
        news_count=request_data.news_count,
        topics_data=topics_data,
        model_type=model_type,
        model_name=model_name,
        news_urls=news_urls,
    )

    record = {
        "record_id": record["id"],
        "mode": record["mode"],
        "topic_name": record.get("topic_name"),
        "news_source": record["news_source"],
        "news_count": record["news_count"],
        "topics_data": record["topics_data"],
        "model_type": record["model_type"],
        "model_name": record["model_name"],
        "news_urls": record.get("news_urls", []),
    }

    return record


@router.get('/history')
async def get_tweet_topics_history(current_user_id: int = Depends(get_current_user)):
    """获取推文选题历史"""
    with Database.get_cursor() as cursor:
        cursor.execute("SELECT username FROM users WHERE id = %s", (current_user_id,))
        user_row = cursor.fetchone()
        username = user_row['username'] if user_row else f"user_{current_user_id}"

    history = load_tweet_topics_history(username)
    history_sorted = list(reversed(history))
    return history_sorted


@router.delete('/{record_id}')
async def delete_tweet_topics_history(
    record_id: int,
    current_user_id: int = Depends(get_current_user),
):
    """删除推文选题历史记录"""
    with Database.get_cursor() as cursor:
        cursor.execute("SELECT username FROM users WHERE id = %s", (current_user_id,))
        user_row = cursor.fetchone()
        username = user_row['username'] if user_row else f"user_{current_user_id}"

    delete_tweet_topics_record(username, record_id)
    return {"success": True}


@router.post('/generate-intelligent', response_model=IntelligentGenerateResponse)
async def generate_intelligent_topics(
    request_data: IntelligentGenerateRequest,
    current_user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """智能模式生成推文选题"""
    # 获取用户信息
    with Database.get_cursor() as cursor:
        cursor.execute("SELECT username FROM users WHERE id = %s", (current_user_id,))
        user_row = cursor.fetchone()
        username = user_row['username'] if user_row else f"user_{current_user_id}"

    model_type, model_name = _resolve_writer_model(current_user_id)
    _ensure_writer_provider_ready(model_type)

    # 确定主题
    topic_name = None
    if request_data.topic_id:
        # 从数据库获取已保存的主题
        repo = UserTopicsRepository(db)
        topic = await repo.get_topic_by_id(current_user_id, request_data.topic_id)
        if not topic:
            raise HTTPException(status_code=404, detail="主题不存在")
        topic_name = topic['topic_name']
    elif request_data.custom_topic:
        topic_name = request_data.custom_topic
        # 如果需要保存
        if request_data.save_topic:
            try:
                repo = UserTopicsRepository(db)
                await repo.create_user_topic(
                    current_user_id, request_data.custom_topic, request_data.topic_description
                )
            except ValueError:
                # 主题已存在，忽略
                pass
    else:
        raise HTTPException(status_code=400, detail="必须提供主题ID或自定义主题")

    logger.info(f"用户 {current_user_id} 使用智能模式生成选题，主题: {topic_name}")

    # 从全部新闻源获取新闻
    news_sources = ["澎湃科技", "SOTA开源项目", "实时新闻", "新浪直播"]
    all_news = []

    for source in news_sources:
        try:
            source_news = fetch_news_by_source(source, 15)
            all_news.extend(source_news)
            logger.info(f"从 {source} 获取到 {len(source_news)} 条新闻")
        except Exception as exc:
            logger.warning(f"获取 {source} 新闻失败: {exc}")

    if not all_news:
        raise HTTPException(status_code=500, detail="未能获取到任何新闻内容")

    logger.info(f"总共获取到 {len(all_news)} 条新闻")

    # 提取新闻 URL（如果有）
    news_urls = [news.get('url', '') for news in all_news if news.get('url')]

    # 格式化新闻内容
    news_content = format_news_for_prompt(all_news)

    # 构建智能筛选prompt
    prompt = f"""用户关注的主题是：{topic_name}

以下是从多个新闻源获取的热点新闻：

<news_content>
{news_content}
</news_content>

请执行以下任务：
1. 筛选出与主题"{topic_name}"最相关的新闻（最多20条）
2. 从筛选后的新闻中，选出最有价值的{min(request_data.topic_count, 10)}个选题方向
3. 对每个选题进行价值评估（考虑：热度、原创性、时效性、传播潜力）

返回JSON格式，包含以下字段：
- filtered_news: 筛选后的新闻列表，每条包含 title, relevance_score, reason
- topics: 选题列表
- summary: 整体总结
- hot_keywords: 热门关键词列表
"""

    try:
        response = chat(
            prompt=prompt,
            system_prompt=pt.TWEET_TOPIC_GENERATOR,
            model_type=model_type,
            model_name=model_name,
            max_tokens=16384,
        )
    except Exception as exc:
        logger.error(f"智能模式生成选题失败: {exc}", exc_info=True)
        if '提供商' in str(exc) or 'API Key' in str(exc):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(exc),
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'生成选题失败: {str(exc)}',
        ) from exc

    topics_data = parse_llm_response(response)
    if not topics_data or not topics_data.get('topics'):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='LLM生成选题失败',
        )

    # 为每个topic匹配对应的URL
    topics_data = match_urls_to_topics(all_news, topics_data)

    record = add_tweet_topics_record(
        username=username,
        news_source="all",
        news_count=len(all_news),
        topics_data=topics_data,
        model_type=model_type,
        model_name=model_name,
        mode="intelligent",
        topic_name=topic_name,
        news_urls=news_urls,
    )

    return {
        "record_id": record["id"],
        "mode": "intelligent",
        "topic_name": topic_name,
        "news_source": "all",
        "news_count": len(all_news),
        "topics_data": topics_data,
        "model_type": model_type,
        "model_name": model_name,
        "news_urls": news_urls,
    }


@router.get('/user-topics')
async def get_user_topics(
    current_user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取用户的所有主题"""
    repo = UserTopicsRepository(db)
    topics = await repo.get_user_topics(current_user_id)
    return {"topics": topics}


@router.post('/user-topics')
async def create_user_topic(
    request_data: CreateTopicRequest,
    current_user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """创建新主题"""
    try:
        repo = UserTopicsRepository(db)
        topic = await repo.create_user_topic(
            current_user_id, request_data.topic_name, request_data.description
        )
        return {"topic": topic}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete('/user-topics/{topic_id}')
async def delete_user_topic(
    topic_id: int,
    current_user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除主题"""
    repo = UserTopicsRepository(db)
    success = await repo.delete_user_topic(current_user_id, topic_id)
    if not success:
        raise HTTPException(status_code=404, detail="主题不存在")

    return {"success": True}


# ============ 辅助方法 ============

def fetch_news_by_source(source_name: str, count: int = 15) -> List[Dict[str, Any]]:
    try:
        if source_name == '澎湃科技':
            return fetch_thepaper_tech_news(count)
        if source_name == 'SOTA开源项目':
            return fetch_sota_projects(count)
        if source_name == '实时新闻':
            return fetch_chinaz_news(news_type=1, count=count)
        if source_name == '新浪直播':
            return fetch_sina_live_news(count)
        logger.warning(f"未知新闻源: {source_name}")
        return []
    except Exception as exc:
        logger.error(f"获取新闻失败: {exc}")
        return []


def fetch_thepaper_tech_news(count: int = 15) -> List[Dict[str, Any]]:
    try:
        url = 'https://api.thepaper.cn/contentapi/nodeCont/getByChannelId'
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Content-Type': 'application/json',
            'Referer': 'https://www.thepaper.cn/',
        }
        payload = {
            'channelId': '119908',
            'excludeContIds': [],
            'listRecommendIds': [],
            'province': None,
            'pageSize': count,
            'startTime': None,
            'pageNum': 1,
        }
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        if response.status_code == 200:
            data = response.json()
            articles = data.get('data', {}).get('list', [])
            news_list = []
            for article in articles[:count]:
                news_list.append({
                    'title': article.get('name', ''),
                    'summary': '',
                    'published_at': article.get('pubTime', ''),
                    'source': '澎湃科技',
                })
            return news_list
        return []
    except Exception as exc:
        logger.error(f"获取澎湃科技新闻失败: {exc}")
        return []


def fetch_sota_projects(count: int = 15) -> List[Dict[str, Any]]:
    try:
        url = f"https://sota.jiqizhixin.com/api/v2/sota/terms?order=generationAt&per={count}&page=1"
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            data = response.json()
            projects = data.get('data', [])
            news_list = []
            for project in projects[:count]:
                source = project.get('source', {})
                news_list.append({
                    'title': source.get('name', ''),
                    'summary': source.get('summary', source.get('desc', '')),
                    'published_at': '',
                    'source': 'SOTA开源项目',
                })
            return news_list
        return []
    except Exception as exc:
        logger.error(f"获取SOTA项目失败: {exc}")
        return []


def fetch_chinaz_news(news_type: int, count: int = 15) -> List[Dict[str, Any]]:
    try:
        url = (
            'https://app.chinaz.com/djflkdsoisknfoklsyhownfrlewfknoiaewf/ai/'
            f'GetAiInfoList.aspx?flag=zh_cn&type={news_type}&page=1&pagesize={count}'
        )
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Referer': 'https://app.chinaz.com/',
            'Accept': 'application/json, text/plain, */*',
        }
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code == 200:
            data = response.json()
            news_items = data if isinstance(data, list) else data.get('data', [])
            news_list = []
            for item in news_items[:count]:
                news_list.append({
                    'title': clean_html_text(item.get('title', '')),
                    'summary': clean_html_text(item.get('description', item.get('summary', ''))),
                    'published_at': item.get('addtime', ''),
                    'source': item.get('sourcename', '站长之家'),
                })
            return news_list
        return []
    except Exception as exc:
        logger.error(f"获取站长之家新闻失败: {exc}")
        return []


def fetch_sina_live_news(count: int = 15) -> List[Dict[str, Any]]:
    """获取新浪直播新闻"""
    try:
        url = f"https://feed.mix.sina.com.cn/api/roll/get?pageid=153&lid=2509&k=&num={count}&page=1"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Referer': 'https://news.sina.com.cn/',
        }
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code == 200:
            data = response.json()
            news_list = data.get('result', {}).get('data', [])
            result = []
            for item in news_list[:count]:
                result.append({
                    'title': clean_html_text(item.get('title', '')),
                    'summary': clean_html_text(item.get('intro', '')),
                    'url': item.get('url', ''),
                    'published_at': item.get('ctime', ''),
                    'source': '新浪直播'
                })
            return result
        return []
    except Exception as exc:
        logger.error(f"获取新浪直播新闻失败: {exc}")
        return []


def clean_html_text(text: str) -> str:
    if not text:
        return ''
    text = re.sub(r'<[^>]+>', '', str(text))
    import html
    text = html.unescape(text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def format_news_for_prompt(news_data: List[Dict[str, Any]]) -> str:
    formatted = []
    for idx, news in enumerate(news_data, 1):
        title = news.get('title', '无标题')
        summary = news.get('summary', '无摘要')
        published_at = news.get('published_at', '')
        source = news.get('source', '')
        url = news.get('url', '')

        news_text = f"""【新闻{idx}】
标题：{title}
来源：{source}
时间：{published_at}
链接：{url}
内容：{summary}
---"""
        formatted.append(news_text)

    return "\n\n".join(formatted)


def parse_llm_response(response: str) -> Optional[Dict[str, Any]]:
    logger.debug(f"开始解析LLM响应，响应长度: {len(response)}")

    def try_fix_truncated_json(json_str: str) -> str:
        fixed = json_str.strip()

        def smart_complete(text: str) -> str:
            stack = []
            in_string = False
            escape_next = False

            for char in text:
                if escape_next:
                    escape_next = False
                    continue
                if char == '\\':
                    escape_next = True
                    continue
                if char == '"':
                    in_string = not in_string
                    continue
                if in_string:
                    continue
                if char == '{':
                    stack.append('}')
                elif char == '[':
                    stack.append(']')
                elif char == '}' and stack and stack[-1] == '}':
                    stack.pop()
                elif char == ']' and stack and stack[-1] == ']':
                    stack.pop()
            return text + ''.join(reversed(stack))

        test_json = smart_complete(fixed)
        try:
            json.loads(test_json)
            return test_json
        except json.JSONDecodeError:
            pass

        value_end_pattern = r'("[^\"]*"|\]|\})'
        matches = list(re.finditer(value_end_pattern, fixed))
        for match in reversed(matches[-30:]):
            pos = match.end()
            test_fixed = fixed[:pos].rstrip().rstrip(',').rstrip()
            try:
                test_json = smart_complete(test_fixed)
                json.loads(test_json)
                return test_json
            except json.JSONDecodeError:
                continue

        return smart_complete(fixed)

    def extract_and_parse(text: str) -> Optional[Dict[str, Any]]:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        json_match = re.search(r'```(?:json|JSON)?\s*(.*?)\s*```', text, re.DOTALL | re.IGNORECASE)
        if json_match:
            json_str = json_match.group(1).strip()
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                try:
                    fixed = try_fix_truncated_json(json_str)
                    return json.loads(fixed)
                except Exception:
                    pass

        json_match = re.search(r'```(?:json|JSON)?\s*(\{.*)', text, re.DOTALL | re.IGNORECASE)
        if json_match:
            json_str = json_match.group(1).strip()
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                try:
                    fixed = try_fix_truncated_json(json_str)
                    return json.loads(fixed)
                except Exception:
                    pass

        json_match = re.search(r'\{.*', text, re.DOTALL)
        if json_match:
            json_str = json_match.group(0).strip()
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                try:
                    fixed = try_fix_truncated_json(json_str)
                    return json.loads(fixed)
                except Exception:
                    pass

        return None

    result = extract_and_parse(response)
    if result:
        logger.info(f"成功解析推文选题JSON，包含 {len(result.get('topics', []))} 个选题")
        return result

    logger.error("无法解析LLM响应")
    return None


def match_urls_to_topics(news_data: List[Dict[str, Any]], topics_data: Dict[str, Any]) -> Dict[str, Any]:
    """根据LLM返回的source_news_title匹配对应的URL"""
    # 创建标题到URL的映射
    title_to_url = {}
    for news in news_data:
        title = news.get('title', '')
        url = news.get('url', '')
        if title and url:
            # 使用标题的前20个字符作为匹配键，处理可能截断的情况
            title_key = title[:30]
            title_to_url[title_key] = url

    # 为每个topic添加匹配的URL
    topics = topics_data.get('topics', [])
    for topic in topics:
        source_title = topic.get('source_news_title', '')
        if source_title:
            # 尝试精确匹配
            if source_title in title_to_url:
                topic['source_urls'] = [title_to_url[source_title]]
            else:
                # 尝试模糊匹配（使用前30个字符）
                source_key = source_title[:30]
                matched = False
                for title_key, url in title_to_url.items():
                    if source_key in title_key or title_key in source_key:
                        topic['source_urls'] = [url]
                        matched = True
                        break
                if not matched:
                    topic['source_urls'] = []
        else:
            topic['source_urls'] = []

    return topics_data
