# -*- coding: utf-8 -*-
"""
文章生成增强 API 路由
支持 SSE 流式进度推送和 Redis 队列管理
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import StreamingResponse
from typing import Optional, List, Dict, Any
import logging
import json
import uuid
from datetime import datetime, timezone

from backend.api.core.dependencies import get_current_user
from backend.api.core.redis_client import redis_client
from backend.api.services.article_generator import article_generator
from backend.api.services.tier_service import TierService
from utils.database import Database

logger = logging.getLogger(__name__)
router = APIRouter()
RUNNING_QUEUE_STATUSES = {"queued", "running"}
STALE_TASK_SECONDS = 600


def _parse_timestamp(value: Any) -> Optional[datetime]:
    """Best-effort ISO timestamp parsing."""
    if not value:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            return None
    return None


async def _mark_task_interrupted(
    user_id: int,
    article_id: str,
    topic: str = "",
    reason: str = "任务在服务重载或中断后未继续执行",
) -> None:
    """Mark an in-flight task as interrupted and remove it from the visible queue."""
    await redis_client.set_article_progress(article_id, {
        "status": "failed",
        "progress_percent": 0,
        "current_step": "任务已中断，请重试",
        "error_message": reason,
        "topic": topic,
    })
    await redis_client.remove_from_queue(user_id, article_id)

    with Database.get_cursor() as cursor:
        cursor.execute("""
            UPDATE articles
            SET status = 'failed', updated_at = NOW()
            WHERE id = %s AND user_id = %s AND status IN ('queued', 'generating')
        """, (article_id, user_id))


async def _reconcile_queue_item(
    user_id: int,
    article_id: str,
    progress: Optional[Dict[str, Any]],
    *,
    now: Optional[datetime] = None,
    stale_after_seconds: int = STALE_TASK_SECONDS,
) -> Optional[Dict[str, Any]]:
    """Hide zombie queue items that were interrupted mid-generation."""
    if not progress:
        return None

    status_value = progress.get("status", "queued")
    task_status = status_value.decode() if isinstance(status_value, bytes) else str(status_value)
    if task_status not in RUNNING_QUEUE_STATUSES:
        return progress

    with Database.get_cursor() as cursor:
        cursor.execute("""
            SELECT status, topic, created_at, updated_at FROM articles
            WHERE id = %s AND user_id = %s
        """, (article_id, user_id))
        article_row = cursor.fetchone()

    if not article_row or article_row.get("status") not in {"queued", "generating"}:
        return progress

    current_time = now or datetime.now(timezone.utc)
    last_update = (
        _parse_timestamp(progress.get("updated_at"))
        or _parse_timestamp(article_row.get("updated_at"))
        or _parse_timestamp(article_row.get("created_at"))
    )
    if last_update is None:
        return progress

    age_seconds = (current_time - last_update).total_seconds()
    if age_seconds <= stale_after_seconds:
        return progress

    topic = progress.get("topic") or article_row.get("topic") or ""
    await _mark_task_interrupted(user_id, article_id, topic=topic)
    logger.warning(
        "清理僵尸文章任务: user=%s, task=%s, stale_for=%.1fs",
        user_id,
        article_id,
        age_seconds,
    )
    return None


# ============ 数据模型 ============

from pydantic import BaseModel, Field, field_validator

class ArticleGenerateRequest(BaseModel):
    """文章生成请求"""
    topic: str = Field(..., min_length=1, max_length=1000, description="文章主题")
    model_type: Optional[str] = Field('deepseek', description="模型类型")
    model_name: Optional[str] = Field('deepseek-chat', description="模型名称")
    knowledge_document_ids: Optional[List[str]] = Field(None, description="知识库文档ID列表")
    custom_style: Optional[str] = Field("", description="自定义风格")
    user_idea: Optional[str] = Field(
        None, max_length=5000,
        description="用户的想法/观点（用于指导文章方向）"
    )
    user_references: Optional[str] = Field(
        None, max_length=50000,
        description="用户贴入的参考文字（系统将搜索补充素材后结合生成文章）"
    )

    @field_validator('user_idea', 'user_references')
    @classmethod
    def normalize_empty(cls, v):
        if v is not None and v.strip() == '':
            return None
        return v

class ProgressResponse(BaseModel):
    """进度查询响应"""
    article_id: str
    status: str
    progress_percent: int
    current_step: str
    error_message: Optional[str] = None
    content: Optional[str] = None
    outline: Optional[dict] = None


# ============ 文章生成（任务创建）============

@router.post("/generate")
async def generate_article(
    request_data: ArticleGenerateRequest,
    current_user_id: int = Depends(get_current_user)
):
    """
    创建文章生成任务并在后台启动生成。
    前端拿到 task_id 后可通过 GET /generate/stream/{task_id} 接收 SSE 进度。
    """
    import asyncio

    # 检查用户配额
    quota_info = TierService.check_user_quota(current_user_id)
    if not quota_info.get('allowed', False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "message": "本月文章配额已用完",
                "used": quota_info.get('used', 0),
                "limit": quota_info.get('limit', 5),
                "remaining": quota_info.get('remaining', 0)
            }
        )

    # ===== 等级验证：检查用户是否有权限使用请求的模型 =====
    user_tier = TierService.get_user_tier(current_user_id)
    available_models = TierService.get_tier_available_models(user_tier)

    # 获取请求的模型（优先使用请求参数，否则使用用户配置的writer_model）
    model_to_check = request_data.model_name if request_data.model_name else None
    if not model_to_check:
        # 从用户配置获取默认 writer_model
        with Database.get_cursor() as cursor:
            cursor.execute("SELECT writer_model FROM user_model_configs WHERE user_id = %s", (current_user_id,))
            model_row = cursor.fetchone()
            if model_row and model_row['writer_model']:
                # 解析 "provider:model" 格式
                writer_model = model_row['writer_model']
                if ':' in writer_model:
                    model_to_check = writer_model.split(':', 1)[1]
                else:
                    model_to_check = writer_model

    if model_to_check:
        # 检查模型是否在用户可用模型列表中
        model_allowed = any(m['model'] == model_to_check for m in available_models)
        if not model_allowed:
            logger.warning(f"User {current_user_id} (tier: {user_tier}) attempted to use unauthorized model: {model_to_check}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"该模型 ({model_to_check}) 不在您的会员等级可用范围内，请升级会员或选择其他模型"
            )
    # ===== 等级验证结束 =====

    # 验证 LLM 配置是否可用
    try:
        from utils.llm_chat import _get_db_llm_providers
        providers = _get_db_llm_providers()
        if not providers:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="没有可用的 LLM 提供商配置，请在系统设置中配置 API Key"
            )

        # 检查第一个可用的提供商是否有 API key
        first_provider = list(providers.keys())[0]
        if not providers[first_provider].get('api_key'):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"提供商 {first_provider} 没有配置 API Key，请在系统设置中配置"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"验证 LLM 配置失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"验证 LLM 配置失败: {str(e)}"
        )

    article_id = str(uuid.uuid4())
    now = datetime.utcnow()

    logger.info(f"创建文章生成任务: user={current_user_id}, article_id={article_id}, topic={request_data.topic}, quota_remaining={quota_info.get('remaining', 0)}")

    # 初始化 Redis 进度
    await redis_client.set_article_progress(article_id, {
        "status": "queued",
        "progress_percent": "0",
        "current_step": "等待中",
        "topic": request_data.topic,
    })

    # 添加到用户队列
    await redis_client.add_to_user_queue(current_user_id, article_id)

    # 后台启动文章生成（消费 async generator，驱动 Redis 进度更新）
    async def _run_generation():
        try:
            # 查询用户信息和全局模型配置
            with Database.get_cursor() as cursor:
                cursor.execute("SELECT username FROM users WHERE id = %s", (current_user_id,))
                user_row = cursor.fetchone()
                username = user_row['username'] if user_row else f"user_{current_user_id}"
                
                # 获取用户的全局writer模型配置
                cursor.execute("""
                    SELECT writer_model FROM user_model_configs WHERE user_id = %s
                """, (current_user_id,))
                model_row = cursor.fetchone()
                writer_model = model_row['writer_model'] if model_row else 'deepseek:deepseek-chat'
            
            # 解析模型配置 (格式: provider:model_name)
            if ':' in writer_model:
                model_type, model_name = writer_model.split(':', 1)
            else:
                model_type = 'deepseek'
                model_name = writer_model
            
            # 创建数据库记录（title 先用 topic 占位，生成完成后更新）
            with Database.get_cursor() as cursor:
                cursor.execute("""
                    INSERT INTO articles (id, user_id, username, topic, title, status, word_count, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, 'generating', 0, NOW(), NOW())
                """, (article_id, current_user_id, username, request_data.topic, request_data.topic))
            
            # 收集生成过程中的数据
            article_content = ""
            article_outline = None
            article_metadata = None
            
            async for _event in article_generator.generate_article_stream(
                topic=request_data.topic,
                user_id=current_user_id,
                article_id=article_id,
                model_type=model_type,
                model_name=model_name,
                knowledge_document_ids=request_data.knowledge_document_ids,
                custom_style=request_data.custom_style or "",
                user_idea=request_data.user_idea,
                user_references=request_data.user_references,
            ):
                # 收集完成事件中的内容
                if _event.get("type") == "completed" and _event.get("data"):
                    article_content = _event["data"].get("content", "")
                    article_metadata = _event["data"].get("article_metadata")
                # 收集大纲
                if _event.get("data", {}).get("outline"):
                    article_outline = _event["data"]["outline"]
            
            # 生成完成后保存到数据库
            if article_content:
                # 从内容中提取标题（第一行的 # 标题）
                import re
                title_match = re.match(r'^#\s+(.+)$', article_content, re.MULTILINE)
                article_title = title_match.group(1) if title_match else request_data.topic
                
                # 构建完整的 metadata（包含模型、搜索、图片、参考来源等详情）
                metadata_to_save = article_metadata or {}
                metadata_to_save['outline'] = article_outline
                
                with Database.get_cursor() as cursor:
                    cursor.execute("""
                        UPDATE articles
                        SET title = %s, content = %s, outline = %s, 
                            model_type = %s, model_name = %s,
                            spider_num = %s, custom_style = %s,
                            image_enabled = %s,
                            metadata = %s,
                            status = 'completed',
                            completed_at = NOW(), updated_at = NOW()
                        WHERE id = %s
                    """, (
                        article_title, 
                        article_content, 
                        json.dumps(article_outline) if article_outline else None,
                        model_type,
                        model_name,
                        metadata_to_save.get('spider_num'),
                        metadata_to_save.get('custom_style', ''),
                        metadata_to_save.get('image_enabled', True),
                        json.dumps(metadata_to_save, ensure_ascii=False),
                        article_id
                    ))
                
                logger.info(f"文章已保存到数据库: article_id={article_id}, title={article_title}")
        except asyncio.CancelledError:
            logger.warning(f"后台文章生成被取消: article_id={article_id}")
            try:
                await _mark_task_interrupted(
                    current_user_id,
                    article_id,
                    topic=request_data.topic,
                )
            except Exception as cleanup_error:
                logger.error(f"取消任务清理失败: article_id={article_id}, error={cleanup_error}")
            raise
        except Exception as e:
            logger.error(f"后台文章生成失败: article_id={article_id}, error={e}", exc_info=True)
            await redis_client.set_article_progress(article_id, {
                "status": "failed",
                "progress_percent": "0",
                "current_step": "生成失败",
                "error_message": str(e),
            })
            await redis_client.remove_from_queue(current_user_id, article_id)
            # 更新数据库状态为失败
            try:
                with Database.get_cursor() as cursor:
                    cursor.execute("""
                        UPDATE articles SET status = 'failed', updated_at = NOW()
                        WHERE id = %s
                    """, (article_id,))
            except:
                pass

    asyncio.create_task(_run_generation())

    return {
        "task_id": article_id,
        "user_id": current_user_id,
        "topic": request_data.topic,
        "status": "queued",
        "progress": 0,
        "progress_text": "任务已创建，正在启动生成",
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "article_type": request_data.model_type,
    }


# ============ 配额查询 ============

@router.get("/quota")
async def get_user_quota(
    current_user_id: int = Depends(get_current_user)
):
    """
    获取用户文章配额信息

    Returns:
        {
            "tier": "free" | "pro" | "ultra",
            "used": 已用篇数,
            "limit": 配额上限,
            "remaining": 剩余篇数,
            "allowed": 是否可以继续生成
        }
    """
    quota_info = TierService.check_user_quota(current_user_id)
    tier = TierService.get_user_tier(current_user_id)

    return {
        "tier": tier,
        "used": quota_info.get('used', 0),
        "limit": quota_info.get('limit', 5),
        "remaining": quota_info.get('remaining', 0),
        "allowed": quota_info.get('allowed', False)
    }


# ============ 文章生成（SSE 流式）============

@router.post("/generate/stream")
async def generate_article_stream(
    request_data: ArticleGenerateRequest,
    current_user_id: int = Depends(get_current_user)
):
    """
    流式生成文章（SSE）

    返回 Server-Sent Events 流，实时推送生成进度
    """
    # 检查用户配额
    quota_info = TierService.check_user_quota(current_user_id)
    if not quota_info.get('allowed', False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "message": "本月文章配额已用完",
                "used": quota_info.get('used', 0),
                "limit": quota_info.get('limit', 5),
                "remaining": quota_info.get('remaining', 0)
            }
        )

    # ===== 等级验证：检查用户是否有权限使用请求的模型 =====
    user_tier = TierService.get_user_tier(current_user_id)
    available_models = TierService.get_tier_available_models(user_tier)

    # 获取请求的模型
    model_to_check = request_data.model_name
    if model_to_check:
        # 检查模型是否在用户可用模型列表中
        model_allowed = any(m['model'] == model_to_check for m in available_models)
        if not model_allowed:
            logger.warning(f"User {current_user_id} (tier: {user_tier}) attempted to use unauthorized model: {model_to_check}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"该模型 ({model_to_check}) 不在您的会员等级可用范围内，请升级会员或选择其他模型"
            )
    # ===== 等级验证结束 =====

    # 验证 LLM 配置是否可用
    try:
        from utils.llm_chat import _get_db_llm_providers
        providers = _get_db_llm_providers()
        if not providers:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="没有可用的 LLM 提供商配置，请在系统设置中配置 API Key"
            )

        # 解析请求的模型
        model_type = request_data.model_type
        model_name = request_data.model_name

        if model_type:
            # 验证该提供商是否有 API key
            if model_type in providers:
                if not providers[model_type].get('api_key'):
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail=f"提供商 {model_type} 没有配置 API Key，请在系统设置中配置"
                    )
            else:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"提供商 {model_type} 不存在，请在系统设置中配置"
                )
        else:
            # 没有指定模型类型，检查第一个可用的提供商
            first_provider = list(providers.keys())[0]
            if not providers[first_provider].get('api_key'):
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"提供商 {first_provider} 没有配置 API Key，请在系统设置中配置"
                )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"验证 LLM 配置失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"验证 LLM 配置失败: {str(e)}"
        )

    # 生成文章ID
    article_id = str(uuid.uuid4())

    logger.info(f"开始生成文章: user={current_user_id}, article_id={article_id}, topic={request_data.topic}, quota_remaining={quota_info.get('remaining', 0)}")
    
    # 创建数据库记录（title 先用 topic 占位，生成完成后更新）
    with Database.get_cursor() as cursor:
        cursor.execute("""
            INSERT INTO articles (id, user_id, topic, title, status, word_count, created_at, updated_at)
            VALUES (%s, %s, %s, %s, 'generating', 0, NOW(), NOW())
            RETURNING id
        """, (article_id, current_user_id, request_data.topic, request_data.topic))
    
    # 添加到用户队列
    await redis_client.add_to_user_queue(current_user_id, article_id)
    
    async def event_generator():
        """SSE 事件生成器"""
        try:
            async for progress_event in article_generator.generate_article_stream(
                topic=request_data.topic,
                user_id=current_user_id,
                article_id=article_id,
                model_type=request_data.model_type,
                model_name=request_data.model_name,
                knowledge_document_ids=request_data.knowledge_document_ids,
                custom_style=request_data.custom_style,
                user_idea=request_data.user_idea,
                user_references=request_data.user_references,
            ):
                # SSE 格式
                event_data = json.dumps(progress_event, ensure_ascii=False)
                yield f"data: {event_data}\n\n"
                
                # 如果完成，更新数据库
                if progress_event.get("type") == "completed":
                    content = progress_event.get("data", {}).get("content", "")
                    with Database.get_cursor() as cursor:
                        cursor.execute("""
                            UPDATE articles
                            SET content = %s, status = 'completed', 
                                completed_at = NOW(), updated_at = NOW()
                            WHERE id = %s
                        """, (content, article_id))
                
                # 如果失败，更新数据库
                elif progress_event.get("type") == "error":
                    error_msg = progress_event.get("error_message", "Unknown error")
                    with Database.get_cursor() as cursor:
                        cursor.execute("""
                            UPDATE articles
                            SET status = 'failed', updated_at = NOW()
                            WHERE id = %s
                        """, (article_id,))
            
            # 发送完成信号
            yield "data: [DONE]\n\n"
            
        except Exception as e:
            logger.error(f"SSE 流生成失败: {e}", exc_info=True)
            error_event = {
                "type": "error",
                "article_id": article_id,
                "error_message": str(e)
            }
            yield f"data: {json.dumps(error_event, ensure_ascii=False)}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # 禁用 Nginx 缓冲
        }
    )


# ============ SSE 进度流（按 task_id 查询）============

@router.get("/generate/stream/{article_id}")
async def stream_article_progress(
    article_id: str,
    request: Request,
):
    """
    通过 SSE 流式推送已有任务的生成进度。
    前端先调用 POST /generate 创建任务，再用此接口轮询进度。
    """
    from backend.api.core.security import verify_token

    # 验证身份
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    token = auth_header.split(" ")[1]
    current_user_id = verify_token(token)
    if current_user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    async def event_generator():
        import asyncio
        max_polls = 600          # 最多轮询 10 分钟（600 × 1s）
        polls = 0
        last_status = None

        while polls < max_polls:
            progress = await redis_client.get_article_progress(article_id)

            if progress:
                current_status = progress.get("status", "unknown")
                # 解码 bytes keys if needed
                if isinstance(current_status, bytes):
                    current_status = current_status.decode()

                event = {
                    "task_id": article_id,
                    "type": current_status,
                    "status": current_status,
                    "progress_percent": int(progress.get("progress_percent", 0)),
                    "current_step": progress.get("current_step", ""),
                    "timestamp": datetime.utcnow().isoformat(),
                }

                # 构建 data 字段（使用 setdefault 避免覆盖）
                data = {}
                if progress.get("content"):
                    data["live_article"] = progress["content"]
                if progress.get("error_message"):
                    data["error_message"] = progress["error_message"]
                if progress.get("outline"):
                    try:
                        data["outline"] = json.loads(progress["outline"])
                    except (json.JSONDecodeError, TypeError):
                        pass
                if progress.get("search_results"):
                    try:
                        data["search_results"] = json.loads(progress["search_results"])
                    except (json.JSONDecodeError, TypeError):
                        pass
                if progress.get("search_stats"):
                    try:
                        data["search_stats"] = json.loads(progress["search_stats"])
                    except (json.JSONDecodeError, TypeError):
                        pass
                if progress.get("images"):
                    try:
                        data["images"] = json.loads(progress["images"])
                    except (json.JSONDecodeError, TypeError):
                        pass
                if progress.get("references"):
                    try:
                        data["references"] = json.loads(progress["references"])
                    except (json.JSONDecodeError, TypeError):
                        pass
                if progress.get("article_metadata"):
                    try:
                        data["article_metadata"] = json.loads(progress["article_metadata"])
                    except (json.JSONDecodeError, TypeError):
                        pass
                
                if data:
                    event["data"] = data

                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

                if current_status in ("completed", "failed", "error"):
                    yield "data: [DONE]\n\n"
                    return
            else:
                # 任务尚未开始或已过期
                event = {
                    "task_id": article_id,
                    "type": "pending",
                    "status": "queued",
                    "progress_percent": 0,
                    "current_step": "等待中",
                    "timestamp": datetime.utcnow().isoformat(),
                }
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

            polls += 1
            await asyncio.sleep(1)

        # 超时
        yield f"data: {json.dumps({'type': 'error', 'task_id': article_id, 'data': {'error_message': '进度查询超时'}}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ============ 进度查询 ============

@router.get("/generate/progress/{article_id}", response_model=ProgressResponse)
async def get_article_progress(
    article_id: str,
    current_user_id: int = Depends(get_current_user)
):
    """
    查询文章生成进度
    """
    # 验证文章所有权
    with Database.get_cursor() as cursor:
        cursor.execute("""
            SELECT user_id FROM articles WHERE id = %s
        """, (article_id,))
        row = cursor.fetchone()
        
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="文章不存在"
            )
        
        if row['user_id'] != current_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权访问此文章"
            )
    
    # 从 Redis 获取进度
    progress_data = await redis_client.get_article_progress(article_id)
    
    if not progress_data:
        # 如果 Redis 中没有，从数据库获取
        with Database.get_cursor() as cursor:
            cursor.execute("""
                SELECT status, content FROM articles WHERE id = %s
            """, (article_id,))
            row = cursor.fetchone()
            
            if row['status'] == 'completed':
                return ProgressResponse(
                    article_id=article_id,
                    status='completed',
                    progress_percent=100,
                    current_step='已完成',
                    content=row['content']
                )
            else:
                return ProgressResponse(
                    article_id=article_id,
                    status=row['status'],
                    progress_percent=0,
                    current_step='等待中'
                )
    
    # 返回 Redis 中的进度
    return ProgressResponse(
        article_id=article_id,
        status=progress_data.get('status', 'unknown'),
        progress_percent=int(progress_data.get('progress_percent', 0)),
        current_step=progress_data.get('current_step', ''),
        error_message=progress_data.get('error_message'),
        content=progress_data.get('content'),
        outline=json.loads(progress_data.get('outline', '{}')) if progress_data.get('outline') else None
    )


# ============ 文章列表查询 ============

@router.get("/")
async def list_articles(
    page: int = 1,
    limit: int = 50,
    current_user_id: int = Depends(get_current_user)
):
    """
    获取用户的文章列表
    """
    offset = (page - 1) * limit
    
    with Database.get_cursor() as cursor:
        # 查询文章列表（包含content用于预览和下载，以及详情字段）
        cursor.execute("""
            SELECT id, user_id, username, topic, title, content, status, 
                   model_type, model_name, spider_num, custom_style, image_enabled,
                   metadata,
                   created_at, updated_at, completed_at
            FROM articles
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
        """, (current_user_id, limit, offset))
        
        articles = cursor.fetchall()
        
        # 查询总数
        cursor.execute("""
            SELECT COUNT(*) as total FROM articles WHERE user_id = %s
        """, (current_user_id,))
        total_row = cursor.fetchone()
        total = total_row['total'] if total_row else 0
    
    # 转换为响应格式
    items = []
    for article in articles:
        # 解析 metadata JSON
        metadata = {}
        if article.get('metadata'):
            try:
                metadata = article['metadata'] if isinstance(article['metadata'], dict) else json.loads(article['metadata'])
            except (json.JSONDecodeError, TypeError):
                pass
        
        # 将顶层DB字段合并到metadata中（兼容旧文章没有metadata JSONB的情况）
        if article.get('model_type') and not metadata.get('model_type'):
            metadata['model_type'] = article['model_type']
        if article.get('model_name') and not metadata.get('model_name'):
            metadata['model_name'] = article['model_name']
        if article.get('spider_num') is not None and metadata.get('spider_num') is None:
            metadata['spider_num'] = article['spider_num']
        if article.get('image_enabled') and metadata.get('image_enabled') is None:
            metadata['image_enabled'] = article['image_enabled']
        
        items.append({
            "id": article['id'],
            "user_id": article['user_id'],
            "username": article['username'],
            "topic": article['topic'],
            "title": article['title'],
            "content": article.get('content') or '',
            "status": article['status'],
            "model_type": article.get('model_type'),
            "model_name": article.get('model_name'),
            "spider_num": article.get('spider_num'),
            "image_enabled": article.get('image_enabled', False),
            "metadata": metadata,
            "created_at": article['created_at'].isoformat() if article['created_at'] else None,
            "updated_at": article['updated_at'].isoformat() if article['updated_at'] else None,
            "completed_at": article['completed_at'].isoformat() if article['completed_at'] else None,
        })
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": (total + limit - 1) // limit if total > 0 else 0
    }


# ============ 用户队列管理 ============

@router.get("/queue")
async def get_user_queue(
    request: Request,
    limit: int = 20
):
    """
    获取用户的文章生成队列
    """
    from backend.api.core.security import verify_token
    
    # Try to get user ID from authorization header
    current_user_id = None
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        current_user_id = verify_token(token)
    
    # If not authenticated, return empty queue
    if current_user_id is None:
        return {"items": [], "total": 0}
    
    queue_items = await redis_client.get_user_queue(current_user_id, limit)
    
    # 获取文章 ID 列表
    article_ids = []
    for item in queue_items:
        aid = item[0]
        if isinstance(aid, bytes):
            aid = aid.decode()
        article_ids.append(aid)
    
    if not article_ids:
        return {"items": [], "total": 0}
    
    # 从 Redis 获取每个任务的进度信息，自动清理过期/异常任务
    items = []
    for aid in article_ids:
        progress = await redis_client.get_article_progress(aid)
        reconciled = await _reconcile_queue_item(current_user_id, aid, progress)
        if not reconciled:
            if progress is None:
                try:
                    await redis_client.remove_from_queue(current_user_id, aid)
                    logger.info(f"自动清理过期队列任务: user={current_user_id}, task={aid}")
                except Exception as e:
                    logger.warning(f"清理过期任务失败: {e}")
            continue

        task_status = reconciled.get("status", "queued")
        if isinstance(task_status, bytes):
            task_status = task_status.decode()
        items.append({
            "task_id": aid,
            "topic": reconciled.get("topic", ""),
            "status": task_status,
            "progress": int(reconciled.get("progress_percent", 0)),
            "progress_text": reconciled.get("current_step", ""),
            "error_message": reconciled.get("error_message", ""),
            "created_at": reconciled.get("created_at", datetime.utcnow().isoformat()),
            "updated_at": reconciled.get("updated_at", datetime.utcnow().isoformat()),
        })

    return {"items": items, "total": len(items)}


@router.delete("/queue/{article_id}")
async def remove_from_queue(
    article_id: str,
    current_user_id: int = Depends(get_current_user)
):
    """
    从队列中移除单个任务
    """
    # 从 Redis 队列中移除
    await redis_client.remove_from_queue(current_user_id, article_id)
    
    # 删除进度缓存
    await redis_client.delete_article_progress(article_id)
    
    logger.info(f"手动移除队列任务: user={current_user_id}, task={article_id}")
    return {"message": "已从队列中移除"}


@router.delete("/queue")
async def clear_user_queue(
    request: Request,
):
    """
    清空用户的所有队列任务
    """
    from backend.api.core.security import verify_token
    
    current_user_id = None
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        current_user_id = verify_token(token)
    
    if current_user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    
    # 获取用户队列中的所有任务
    queue_items = await redis_client.get_user_queue(current_user_id, 100)
    
    cleared_count = 0
    for item in queue_items:
        aid = item[0]
        if isinstance(aid, bytes):
            aid = aid.decode()
        # 删除进度缓存
        await redis_client.delete_article_progress(aid)
        # 从队列中移除
        await redis_client.remove_from_queue(current_user_id, aid)
        cleared_count += 1
    
    logger.info(f"清空用户队列: user={current_user_id}, cleared={cleared_count}")
    return {"message": f"已清空 {cleared_count} 个任务", "cleared": cleared_count}


# ============ 公众号格式转换 ============

class WeChatConvertRequest(BaseModel):
    """微信公众号格式转换请求"""
    markdown: str = Field(..., description="Markdown 文本")
    style: Optional[str] = Field("wechat", description="预览风格 (wechat, zhihu, futuristic, elegant)")


class PlatformConvertRequest(BaseModel):
    """多平台格式转换请求"""
    markdown: str = Field(..., description="Markdown 文本")
    platform: str = Field("wechat", description="目标平台: wechat | zhihu | xiaohongshu | toutiao")
    topic: Optional[str] = Field("", description="文章主题（用于标签生成）")

@router.post("/convert/wechat")
async def convert_to_wechat(
    request_data: WeChatConvertRequest,
    current_user_id: int = Depends(get_current_user)
):
    """
    将 Markdown 转换为微信公众号兼容的 HTML（内联样式）
    支持多种自媒体风格
    """
    from utils.wechat_converter import markdown_to_wechat_html
    from backend.api.utils.watermark import inject_watermark_if_needed

    user_tier = TierService.get_user_tier(current_user_id)
    html = markdown_to_wechat_html(request_data.markdown, style=request_data.style)
    html = inject_watermark_if_needed(html, user_tier=user_tier, format="html")
    return {"html": html}


@router.post("/convert/platform")
async def convert_to_platform(
    request_data: PlatformConvertRequest,
    current_user_id: int = Depends(get_current_user)
):
    """多平台格式转换（F3）。"""
    from utils.platform_converter import convert_to_platform as convert_platform_content
    from backend.api.utils.watermark import inject_watermark_if_needed

    try:
        converted = convert_platform_content(
            markdown_content=request_data.markdown,
            platform=request_data.platform,
            topic=request_data.topic or "",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # F2 规则延续：仅 free 用户在输出层注入水印
    user_tier = TierService.get_user_tier(current_user_id)
    if converted.get("format") == "html":
        converted["content"] = inject_watermark_if_needed(
            converted.get("content", ""),
            user_tier=user_tier,
            format="html",
        )
    elif converted.get("format") == "markdown":
        converted["content"] = inject_watermark_if_needed(
            converted.get("content", ""),
            user_tier=user_tier,
            format="markdown",
        )

    return converted


# ============ 单篇文章详情 ============

@router.get("/detail/{article_id}")
async def get_article_detail(
    article_id: str,
    current_user_id: int = Depends(get_current_user)
):
    """
    获取单篇文章详情（含content）
    """
    with Database.get_cursor() as cursor:
        cursor.execute("""
            SELECT id, user_id, username, topic, title, content, outline, status,
                   model_type, model_name, spider_num, custom_style, image_enabled,
                   metadata,
                   created_at, updated_at, completed_at
            FROM articles
            WHERE id = %s AND user_id = %s
        """, (article_id, current_user_id))
        article = cursor.fetchone()
    
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")
    
    # 解析 metadata JSON
    metadata = {}
    if article.get('metadata'):
        try:
            metadata = article['metadata'] if isinstance(article['metadata'], dict) else json.loads(article['metadata'])
        except (json.JSONDecodeError, TypeError):
            pass
    
    # 将顶层DB字段合并到metadata中（兼容旧文章没有metadata JSONB的情况）
    if article.get('model_type') and not metadata.get('model_type'):
        metadata['model_type'] = article['model_type']
    if article.get('model_name') and not metadata.get('model_name'):
        metadata['model_name'] = article['model_name']
    if article.get('spider_num') is not None and metadata.get('spider_num') is None:
        metadata['spider_num'] = article['spider_num']
    if article.get('image_enabled') and metadata.get('image_enabled') is None:
        metadata['image_enabled'] = article['image_enabled']
    
    return {
        "id": article['id'],
        "user_id": article['user_id'],
        "username": article['username'],
        "topic": article['topic'],
        "title": article['title'],
        "content": article.get('content') or '',
        "outline": json.loads(article['outline']) if article.get('outline') else None,
        "status": article['status'],
        "model_type": article.get('model_type'),
        "model_name": article.get('model_name'),
        "spider_num": article.get('spider_num'),
        "custom_style": article.get('custom_style'),
        "image_enabled": article.get('image_enabled', False),
        "metadata": metadata,
        "created_at": article['created_at'].isoformat() if article['created_at'] else None,
        "updated_at": article['updated_at'].isoformat() if article['updated_at'] else None,
        "completed_at": article['completed_at'].isoformat() if article['completed_at'] else None,
    }


# ============ 文章评分（F4） ============

class ScoreResponse(BaseModel):
    """评分响应"""
    total_score: int
    level: str
    summary: str
    dimensions: List[Dict[str, Any]]
    scored_at: str


@router.post("/score/{article_id}", response_model=ScoreResponse)
async def score_article(
    article_id: str,
    current_user_id: int = Depends(get_current_user)
):
    """
    对文章进行质量评分（F4功能）

    包含4个维度：
    - 可读性：基于规则的文本分析
    - 信息密度：LLM分析内容信息量
    - SEO友好度：LLM分析关键词、标题优化
    - 传播力：LLM分析标题吸引度、话题热度

    评分存储到 article_scores 表
    """
    from backend.api.services.article_scoring import ArticleScoringService

    # 验证文章存在
    with Database.get_cursor() as cursor:
        cursor.execute(
            "SELECT id, content FROM articles WHERE id = %s AND user_id = %s",
            (article_id, current_user_id)
        )
        article = cursor.fetchone()

    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")

    content = article.get('content') or article.get('article_content', '')
    title = article.get('title') or article.get('topic', '')

    # 1. 计算可读性评分（基于规则）
    readability = ArticleScoringService.calculate_readability_score(content)

    # 2-4. 其他维度评分（集成LLM）
    dimensions = [readability]

    # 信息密度评分（LLM）
    info_density = await ArticleScoringService.calculate_information_density_score(content, title)
    dimensions.append(info_density)

    # SEO友好度评分（LLM）
    seo_score = await ArticleScoringService.calculate_seo_score(content, title)
    dimensions.append(seo_score)

    # 传播力评分（LLM）
    virality_score = await ArticleScoringService.calculate_virality_score(content, title)
    dimensions.append(virality_score)

    # 计算总分和等级
    total_score = ArticleScoringService.calculate_total_score(dimensions)
    level = ArticleScoringService.get_level(total_score)
    summary = ArticleScoringService.generate_summary(total_score, level, dimensions)

    # 存储评分结果到数据库
    with Database.get_cursor() as cursor:
        cursor.execute("""
            INSERT INTO article_scores (article_id, total_score, level, summary, dimensions)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (article_id) DO UPDATE SET
                total_score = EXCLUDED.total_score,
                level = EXCLUDED.level,
                summary = EXCLUDED.summary,
                dimensions = EXCLUDED.dimensions,
                scored_at = NOW()
        """, (
            article_id,
            total_score,
            level,
            summary,
            json.dumps(dimensions, ensure_ascii=False)
        ))

    return {
        'total_score': total_score,
        'level': level,
        'summary': summary,
        'dimensions': dimensions,
        'scored_at': datetime.now().isoformat()
    }


@router.get("/score/{article_id}", response_model=ScoreResponse)
async def get_article_score(
    article_id: str,
    current_user_id: int = Depends(get_current_user)
):
    """
    获取文章的评分结果
    """
    with Database.get_cursor() as cursor:
        cursor.execute("""
            SELECT article_id, total_score, level, summary, dimensions, scored_at
            FROM article_scores
            WHERE article_id = %s
        """, (article_id,))
        score = cursor.fetchone()

    if not score:
        # 如果没有评分，触发一次评分
        return await score_article(article_id, current_user_id)

    # 处理 dimensions 字段 - PostgreSQL JSONB 可能返回 dict/list 或字符串
    dimensions = score.get('dimensions', [])
    if isinstance(dimensions, str):
        try:
            dimensions = json.loads(dimensions)
        except (json.JSONDecodeError, TypeError):
            dimensions = []

    return {
        'total_score': score['total_score'],
        'level': score['level'],
        'summary': score['summary'],
        'dimensions': dimensions,
        'scored_at': score['scored_at'].isoformat() if score['scored_at'] else None
    }


# ============ 风格分析（F5） ============

class StyleAnalysisRequest(BaseModel):
    """风格分析请求"""
    content: str = Field(..., min_length=500, description="范文内容（至少500字）")


class StyleAnalysisResponse(BaseModel):
    """风格分析响应"""
    style_profile: Dict[str, Any]
    summary: str


@router.post("/style/analyze")
async def analyze_writing_style(
    request_data: StyleAnalysisRequest,
    current_user_id: int = Depends(get_current_user)
):
    """
    分析写作风格（F5功能）

    分析6维度：语气、句式、用词、段落、开头、结尾
    """
    from backend.api.services.style_analyzer import StyleAnalyzerService

    # 执行风格分析
    analysis = StyleAnalyzerService.analyze_sample(request_data.content)

    if 'error' in analysis:
        raise HTTPException(status_code=400, detail=analysis['error'])

    # 生成风格摘要
    style_summary = f"您的写作风格为：{analysis.get('tone', {}).get('label', '中性')}，" \
                   f"句式{analysis.get('sentence_style', {}).get('label', '平衡')}，" \
                   f"用词{analysis.get('vocabulary', {}).get('label', '标准')}。"

    return {
        'style_profile': analysis,
        'summary': style_summary
    }


@router.post("/style/save")
async def save_writing_style(
    request_data: StyleAnalysisRequest,
    current_user_id: int = Depends(get_current_user)
):
    """
    保存写作风格到数据库（F5功能）
    """
    from backend.api.services.style_analyzer import StyleAnalyzerService

    # 执行风格分析
    analysis = StyleAnalyzerService.analyze_sample(request_data.content)

    if 'error' in analysis:
        raise HTTPException(status_code=400, detail=analysis['error'])

    # 检查是否已有风格记录
    with Database.get_cursor() as cursor:
        cursor.execute(
            "SELECT id, sample_filenames FROM user_writing_styles WHERE user_id = %s",
            (current_user_id,)
        )
        existing = cursor.fetchone()

        if existing:
            # 更新现有记录
            current_samples = existing.get('sample_filenames', [])
            # 这里简化处理，实际应该上传文件后记录文件名
            new_samples = current_samples  # 暂时保持不变

            cursor.execute("""
                UPDATE user_writing_styles
                SET style_profile = %s,
                    sample_filenames = %s,
                    sample_count = array_length(%s),
                    updated_at = NOW()
                WHERE user_id = %s
            """, (
                json.dumps(analysis, ensure_ascii=False),
                new_samples,
                new_samples,
                current_user_id
            ))
        else:
            # 创建新记录
            cursor.execute("""
                INSERT INTO user_writing_styles (user_id, style_profile, sample_filenames, sample_count, is_active)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                current_user_id,
                json.dumps(analysis, ensure_ascii=False),
                [],  # 暂时为空，实际应该记录上传的文件名
                0,
                True
            ))

    return {"message": "写作风格已保存", "style_profile": analysis}


@router.get("/style/current")
async def get_current_style(
    current_user_id: int = Depends(get_current_user)
):
    """
    获取当前用户的写作风格
    """
    with Database.get_cursor() as cursor:
        cursor.execute(
            "SELECT style_profile, sample_filenames, sample_count, is_active FROM user_writing_styles WHERE user_id = %s",
            (current_user_id,)
        )
        style = cursor.fetchone()

    if not style:
        return {
            "has_style": False,
            "style_profile": None,
            "sample_count": 0
        }

    return {
        "has_style": True,
        "style_profile": json.loads(style['style_profile']) if style.get('style_profile') else None,
        "sample_filenames": style.get('sample_filenames', []),
        "sample_count": style.get('sample_count', 0),
        "is_active": style.get('is_active', False)
    }


@router.put("/style/toggle")
async def toggle_style(
    is_active: bool = True,
    current_user_id: int = Depends(get_current_user)
):
    """
    开启/关闭写作风格
    """
    with Database.get_cursor() as cursor:
        cursor.execute(
            "UPDATE user_writing_styles SET is_active = %s, updated_at = NOW() WHERE user_id = %s",
            (is_active, current_user_id)
        )

    return {"message": f"写作风格已{'启用' if is_active else '禁用'}"}


@router.delete("/style/delete")
async def delete_style(
    current_user_id: int = Depends(get_current_user)
):
    """
    删除写作风格
    """
    with Database.get_cursor() as cursor:
        cursor.execute(
            "DELETE FROM user_writing_styles WHERE user_id = %s",
            (current_user_id,)
        )

    return {"message": "写作风格已删除"}


# ============ SEO分析（P1 F7） ============

class SEOAnalyzeRequest(BaseModel):
    """SEO分析请求"""
    content: str = Field(..., min_length=1, description="文章内容")
    title: Optional[str] = Field("", description="文章标题")
    article_id: Optional[str] = Field(None, description="文章ID（用于缓存）")


class KeywordDensityInfo(BaseModel):
    """关键词密度信息"""
    keyword: str = Field(..., description="关键词")
    density: float = Field(..., description="密度百分比")
    count: int = Field(..., description="出现次数")
    status: str = Field(..., description="状态: good/acceptable/low/high")
    color: str = Field(..., description="颜色标识: green/yellow/red")
    suggestion: str = Field(..., description="优化建议")


class KeywordAnalysis(BaseModel):
    """关键词分析"""
    keyword: str = Field(..., description="关键词")
    relevance: int = Field(..., description="相关性评分(0-100)")
    density: KeywordDensityInfo = Field(..., description="密度信息")


class TitleOptimization(BaseModel):
    """标题优化结果"""
    score: int = Field(..., description="当前标题评分(0-100)")
    current_title: str = Field(..., description="当前标题")
    feedback: str = Field(..., description="当前标题评价")
    suggestions: List[dict] = Field(default_factory=list, description="优化建议列表")


class MetaDescription(BaseModel):
    """元描述结果"""
    description: str = Field(..., description="生成的元描述")
    length: int = Field(..., description="描述长度")
    status: str = Field(..., description="状态: good/acceptable/needs_improvement")
    color: str = Field(..., description="颜色标识")
    suggestion: str = Field(..., description="优化建议")


class InternalLinkSuggestion(BaseModel):
    """内链建议"""
    article_id: str = Field(..., description="文章ID")
    title: str = Field(..., description="文章标题")
    relevance: int = Field(..., description="相关性评分")
    reason: str = Field(..., description="推荐原因")
    suggested_anchor_text: str = Field(..., description="建议锚文本")


class SEOAnalysisResponse(BaseModel):
    """SEO分析响应"""
    seo_score: dict = Field(..., description="总体SEO评分")
    keywords: List[KeywordAnalysis] = Field(default_factory=list, description="关键词分析")
    title_optimization: TitleOptimization = Field(..., description="标题优化")
    meta_description: MetaDescription = Field(..., description="元描述")
    internal_links: List[InternalLinkSuggestion] = Field(default_factory=list, description="内链建议")


@router.post("/seo/analyze", response_model=SEOAnalysisResponse)
async def analyze_article_seo(
    request_data: SEOAnalyzeRequest,
    current_user_id: int = Depends(get_current_user)
):
    """
    SEO分析接口（P1 F7功能）- V2优化版

    优化点：
    - 单次LLM调用完成所有分析
    - 数据库持久化缓存
    - 先返回旧数据，后台异步更新

    分析内容：
    - 关键词提取（3-5个核心关键词）
    - 关键词密度计算
    - 标题优化建议
    - 元描述生成
    - 内链建议（基于用户历史文章）

    权限要求：Pro及以上用户
    """
    from backend.api.services.seo_analyzer_v2 import SEOAnalyzerServiceV2
    from backend.api.services.tier_service import TierService

    # 检查用户等级权限
    user_tier = TierService.get_user_tier(current_user_id)
    if user_tier == 'free':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "message": "SEO分析功能需要Pro及以上会员",
                "tier": user_tier,
                "required_tier": "pro"
            }
        )

    # 从请求中获取文章ID（如果存在）
    article_id = request_data.article_id if hasattr(request_data, 'article_id') else None

    # 使用V2优化版服务：单次LLM调用 + 数据库持久化
    result = await SEOAnalyzerServiceV2.get_or_create_analysis(
        content=request_data.content,
        title=request_data.title,
        user_id=current_user_id,
        article_id=article_id
    )

    return result


class SEOKeywordExtractRequest(BaseModel):
    """关键词提取请求"""
    content: str = Field(..., min_length=1, description="文章内容")
    title: Optional[str] = Field("", description="文章标题")
    count: Optional[int] = Field(5, ge=1, le=10, description="提取关键词数量")


@router.post("/seo/keywords")
async def extract_seo_keywords(
    request_data: SEOKeywordExtractRequest,
    current_user_id: int = Depends(get_current_user)
):
    """
    提取文章关键词（P1 F7功能）

    权限要求：Pro及以上用户
    """
    from backend.api.services.seo_analyzer import SEOAnalyzerService
    from backend.api.services.tier_service import TierService

    # 检查用户等级权限
    user_tier = TierService.get_user_tier(current_user_id)
    if user_tier == 'free':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "message": "关键词提取功能需要Pro及以上会员",
                "tier": user_tier,
                "required_tier": "pro"
            }
        )

    # 提取关键词
    keywords = await SEOAnalyzerService.extract_keywords(
        content=request_data.content,
        title=request_data.title,
        count=request_data.count
    )

    return {"keywords": keywords}


class SEOTitleOptimizeRequest(BaseModel):
    """标题优化请求"""
    content: str = Field(..., min_length=1, description="文章内容")
    current_title: Optional[str] = Field("", description="当前标题")


@router.post("/seo/optimize-title")
async def optimize_article_title(
    request_data: SEOTitleOptimizeRequest,
    current_user_id: int = Depends(get_current_user)
):
    """
    优化文章标题（P1 F7功能）

    权限要求：Pro及以上用户
    """
    from backend.api.services.seo_analyzer import SEOAnalyzerService
    from backend.api.services.tier_service import TierService

    # 检查用户等级权限
    user_tier = TierService.get_user_tier(current_user_id)
    if user_tier == 'free':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "message": "标题优化功能需要Pro及以上会员",
                "tier": user_tier,
                "required_tier": "pro"
            }
        )

    # 优化标题
    result = await SEOAnalyzerService.optimize_title(
        content=request_data.content,
        current_title=request_data.current_title
    )

    return result


class SEOMetaDescriptionRequest(BaseModel):
    """元描述生成请求"""
    content: str = Field(..., min_length=1, description="文章内容")
    title: Optional[str] = Field("", description="文章标题")


@router.post("/seo/meta-description")
async def generate_meta_description(
    request_data: SEOMetaDescriptionRequest,
    current_user_id: int = Depends(get_current_user)
):
    """
    生成SEO元描述（P1 F7功能）

    权限要求：Pro及以上用户
    """
    from backend.api.services.seo_analyzer import SEOAnalyzerService
    from backend.api.services.tier_service import TierService

    # 检查用户等级权限
    user_tier = TierService.get_user_tier(current_user_id)
    if user_tier == 'free':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "message": "元描述生成功能需要Pro及以上会员",
                "tier": user_tier,
                "required_tier": "pro"
            }
        )

    # 生成元描述
    result = await SEOAnalyzerService.generate_meta_description(
        content=request_data.content,
        title=request_data.title
    )

    return result


class SEOInternalLinksRequest(BaseModel):
    """内链建议请求"""
    content: str = Field(..., min_length=1, description="文章内容")
    article_id: Optional[str] = Field(None, description="当前文章ID（排除）")
    limit: Optional[int] = Field(5, ge=1, le=10, description="返回建议数量")


@router.post("/seo/internal-links")
async def get_internal_link_suggestions(
    request_data: SEOInternalLinksRequest,
    current_user_id: int = Depends(get_current_user)
):
    """
    获取内链建议（P1 F7功能）

    权限要求：Pro及以上用户
    """
    from backend.api.services.seo_analyzer import SEOAnalyzerService
    from backend.api.services.tier_service import TierService

    # 检查用户等级权限
    user_tier = TierService.get_user_tier(current_user_id)
    if user_tier == 'free':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "message": "内链建议功能需要Pro及以上会员",
                "tier": user_tier,
                "required_tier": "pro"
            }
        )

    # 获取内链建议
    suggestions = await SEOAnalyzerService.get_internal_link_suggestions(
        content=request_data.content,
        user_id=current_user_id,
        article_id=request_data.article_id,
        limit=request_data.limit
    )

    return {"suggestions": suggestions}


# ============ 新用户引导（F6） ============

class OnboardingCompleteRequest(BaseModel):
    """引导完成请求"""
    user_role: str = Field(..., description="用户选择的角色")


class OnboardingResponse(BaseModel):
    """引导响应"""
    completed: bool
    user_role: Optional[str]
    completed_at: Optional[str]


@router.get("/onboarding/status")
async def get_onboarding_status(
    current_user_id: int = Depends(get_current_user)
):
    """
    获取用户引导状态（F6功能）
    """
    with Database.get_cursor() as cursor:
        cursor.execute(
            "SELECT completed, user_role, completed_at FROM user_onboarding WHERE user_id = %s",
            (current_user_id,)
        )
        onboarding = cursor.fetchone()

    if not onboarding:
        return {
            "completed": False,
            "user_role": None,
            "completed_at": None
        }

    return {
        "completed": onboarding.get('completed', False),
        "user_role": onboarding.get('user_role'),
        "completed_at": onboarding.get('completed_at').isoformat() if onboarding.get('completed_at') else None
    }


@router.post("/onboarding/complete")
async def complete_onboarding(
    request_data: OnboardingCompleteRequest,
    current_user_id: int = Depends(get_current_user)
):
    """
    完成新用户引导（F6功能）

    Args:
        user_role: 用户选择的角色
        - media_operator: 媒体运营
        - marketer: 市场营销
        - freelancer: 自由职业者
        - personal_ip: 个人博主
    """
    # 验证角色有效性
    valid_roles = ['media_operator', 'marketer', 'freelancer', 'personal_ip']
    if request_data.user_role not in valid_roles:
        raise HTTPException(
            status_code=400,
            detail=f"无效的用户角色，可选: {', '.join(valid_roles)}"
        )

    # 检查是否已有引导记录
    with Database.get_cursor() as cursor:
        cursor.execute(
            "SELECT id, completed FROM user_onboarding WHERE user_id = %s",
            (current_user_id,)
        )
        existing = cursor.fetchone()

        if existing:
            # 更新现有记录
            cursor.execute("""
                UPDATE user_onboarding
                SET completed = %s, user_role = %s, completed_at = NOW()
                WHERE user_id = %s
            """, (True, request_data.user_role, current_user_id))
        else:
            # 创建新记录
            cursor.execute("""
                INSERT INTO user_onboarding (user_id, completed, user_role, completed_at)
                VALUES (%s, %s, %s, NOW())
            """, (current_user_id, True, request_data.user_role))

    return {
        "message": "引导完成",
        "user_role": request_data.user_role
    }


@router.post("/onboarding/skip")
async def skip_onboarding(
    current_user_id: int = Depends(get_current_user)
):
    """
    跳过新用户引导
    """
    with Database.get_cursor() as cursor:
        cursor.execute(
            "SELECT id FROM user_onboarding WHERE user_id = %s",
            (current_user_id,)
        )
        existing = cursor.fetchone()

        if existing:
            # 标记为已完成（跳过也算完成）
            cursor.execute("""
                UPDATE user_onboarding
                SET completed = %s, completed_at = NOW()
                WHERE user_id = %s
            """, (True, current_user_id))
        else:
            # 创建记录（跳过状态）
            cursor.execute("""
                INSERT INTO user_onboarding (user_id, completed, user_role, completed_at)
                VALUES (%s, %s, NULL, NOW())
            """, (current_user_id, True))

    return {"message": "已跳过引导"}


# ============ 文章编辑保存 ============

class ArticleUpdateRequest(BaseModel):
    """文章更新请求"""
    content: str = Field(..., description="文章内容")
    title: Optional[str] = Field(None, description="文章标题")

@router.put("/detail/{article_id}")
async def update_article(
    article_id: str,
    request_data: ArticleUpdateRequest,
    current_user_id: int = Depends(get_current_user)
):
    """
    更新文章内容
    """
    with Database.get_cursor() as cursor:
        # 验证文章存在且属于当前用户
        cursor.execute(
            "SELECT id FROM articles WHERE id = %s AND user_id = %s",
            (article_id, current_user_id)
        )
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="文章不存在")
        
        # 更新内容
        if request_data.title:
            cursor.execute("""
                UPDATE articles SET content = %s, title = %s, updated_at = NOW()
                WHERE id = %s AND user_id = %s
            """, (request_data.content, request_data.title, article_id, current_user_id))
        else:
            cursor.execute("""
                UPDATE articles SET content = %s, updated_at = NOW()
                WHERE id = %s AND user_id = %s
            """, (request_data.content, article_id, current_user_id))
    
    logger.info(f"文章已更新: article_id={article_id}, user_id={current_user_id}")
    return {"message": "文章已保存", "id": article_id}


# ============ 删除文章 ============

@router.delete("/detail/{article_id}")
async def delete_article(
    article_id: str,
    current_user_id: int = Depends(get_current_user)
):
    """
    删除文章
    """
    with Database.get_cursor() as cursor:
        cursor.execute(
            "SELECT id FROM articles WHERE id = %s AND user_id = %s",
            (article_id, current_user_id)
        )
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="文章不存在")
        
        cursor.execute(
            "DELETE FROM articles WHERE id = %s AND user_id = %s",
            (article_id, current_user_id)
        )
    
    logger.info(f"文章已删除: article_id={article_id}, user_id={current_user_id}")
    return {"message": "文章已删除"}
