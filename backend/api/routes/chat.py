# -*- coding: utf-8 -*-
"""
SupaWriter AI 助手路由
处理 AI 聊天、流式响应、会话管理
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from typing import Optional, AsyncGenerator
import logging
import json
import uuid
from datetime import datetime

from backend.api.models.chat import (
    ChatSendRequest,
    ChatSession,
    ChatSessionCreate,
    ChatSessionUpdate,
    ChatSessionResponse,
    ChatMessage
)
from backend.api.core.dependencies import get_current_user, paginate, get_user_tier
from backend.api.services.tier_service import TierService
from backend.api.config import settings


logger = logging.getLogger(__name__)

# 创建路由
router = APIRouter()


# ===== 内部辅助函数 =====

def _create_session_internal(
    user_id: int,
    title: str = "新对话",
    model: Optional[str] = None
) -> dict:
    """
    内部函数：创建新会话

    Args:
        user_id: 用户 ID
        title: 会话标题
        model: 模型名称

    Returns:
        dict: 创建的会话数据
    """
    from utils.database import Database

    session_id = str(uuid.uuid4())

    with Database.get_cursor() as cursor:
        # 获取用户名
        cursor.execute("SELECT username FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        username = user['username'] if user else 'unknown'

        cursor.execute("""
            INSERT INTO chat_sessions
            (id, user_id, username, title, model, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
            RETURNING id, user_id, username, title, model, created_at, updated_at
        """, (session_id, user_id, username, title, model))

        session = cursor.fetchone()

    logger.info(f"Chat session created: id={session_id}, user_id={user_id}")

    return {
        'id': session['id'],
        'user_id': session['user_id'],
        'title': session['title'],
        'model': session.get('model'),
        'created_at': session['created_at'],
        'updated_at': session['updated_at']
    }


def _get_session_messages(session_id: str, limit: int = 20) -> list:
    """
    内部函数：获取会话的历史消息

    Args:
        session_id: 会话 ID
        limit: 最大消息数量

    Returns:
        list: 消息列表，格式为 [{"role": "user", "content": "..."}, ...]
    """
    from utils.database import Database

    with Database.get_cursor() as cursor:
        cursor.execute("""
            SELECT role, content
            FROM chat_messages
            WHERE session_id = %s
            ORDER BY timestamp ASC
            LIMIT %s
        """, (session_id, limit))

        messages = [
            {"role": msg['role'], "content": msg['content']}
            for msg in cursor.fetchall()
        ]

    return messages


def _validate_session_ownership(session_id: str, user_id: int) -> bool:
    """
    内部函数：验证会话所有权

    Args:
        session_id: 会话 ID
        user_id: 用户 ID

    Returns:
        bool: 是否拥有该会话
    """
    from utils.database import Database

    with Database.get_cursor() as cursor:
        cursor.execute(
            "SELECT id FROM chat_sessions WHERE id = %s AND user_id = %s",
            (session_id, user_id)
        )
        return cursor.fetchone() is not None


def _format_search_results_for_llm(sources: list) -> str:
    """
    格式化搜索结果为 LLM 友好的文本

    Args:
        sources: 搜索结果列表，每个包含 {title, url, snippet}

    Returns:
        格式化的文本
    """
    if not sources:
        return "未找到相关搜索结果。"

    formatted_parts = []
    for i, result in enumerate(sources[:10], 1):  # 最多取10条
        part = f"\n[{i}] {result.get('title', '')}\n"
        part += f"    来源: {result.get('url', '')}\n"
        snippet = result.get('snippet', result.get('content', ''))
        if snippet:
            # 限制每条内容长度
            content_preview = snippet[:500] + "..." if len(snippet) > 500 else snippet
            part += f"    内容: {content_preview}\n"
        part += "\n"

        formatted_parts.append(part)

    return "## 搜索结果\n" + "".join(formatted_parts)


# ===== 发送消息（流式响应）=====

@router.post("/send")
async def send_message(
    request_data: ChatSendRequest,
    current_user_id: int = Depends(get_current_user)
):
    """
    发送消息给 AI 助手（SSE 流式响应）

    Args:
        request_data: 聊天请求
        current_user_id: 当前用户 ID

    Returns:
        SSE 流式响应
    """
    from utils.llm_chat import LLMChat, save_message_to_db, update_session_timestamp, _get_db_llm_providers
    from utils.database import Database
    from fastapi import HTTPException

    # 在开始任何操作之前，先验证 LLM 配置是否可用
    try:
        providers = _get_db_llm_providers()
        if not providers:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="没有可用的 LLM 提供商配置，请在系统设置中配置 API Key"
            )

        # 解析请求的模型
        model = request_data.model

        # ===== 等级验证：检查用户是否有权限使用该模型 =====
        user_tier = TierService.get_user_tier(current_user_id)
        available_models = TierService.get_tier_available_models(user_tier)

        # 提取模型名称（处理 "provider:model" 或 "provider/model" 格式）
        if model:
            if '/' in model:
                model_name = model.split('/')[-1]
            elif ':' in model:
                model_name = model.split(':')[-1]
            else:
                model_name = model

            # 检查模型是否在用户可用模型列表中
            model_allowed = any(m['model'] == model_name for m in available_models)
            if not model_allowed:
                logger.warning(f"User {current_user_id} (tier: {user_tier}) attempted to use unauthorized model: {model_name}")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"该模型 ({model_name}) 不在您的会员等级可用范围内，请升级会员或选择其他模型"
                )
        # ===== 等级验证结束 =====

        if model:
            if '/' in model:
                provider_id = model.split('/')[0]
            elif ':' in model:
                provider_id = model.split(':')[0]
            else:
                # 只有模型名，需要查找对应的 provider
                provider_id = None
                for pid, config in providers.items():
                    models = config.get('models', [])
                    for m in models:
                        if isinstance(m, dict) and m.get('name') == model:
                            provider_id = pid
                            break
                        elif m == model:
                            provider_id = pid
                            break
                    if provider_id:
                        break
                if not provider_id:
                    provider_id = list(providers.keys())[0] if providers else None

            # 验证该提供商是否有 API key
            if provider_id and provider_id in providers:
                if not providers[provider_id].get('api_key'):
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail=f"提供商 {provider_id} 没有配置 API Key，请在系统设置中配置"
                    )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"验证 LLM 配置失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"验证 LLM 配置失败: {str(e)}"
        )

    # 获取或创建会话
    session_id = request_data.session_id
    session_created = False

    if not session_id:
        # 创建新会话
        session = _create_session_internal(
            current_user_id,
            title=request_data.message[:20] + "..." if len(request_data.message) > 20 else request_data.message,
            model=request_data.model
        )
        session_id = session['id']
        session_created = True
        logger.info(f"Created new session: {session_id}")
    else:
        # 验证会话所有权（安全检查）
        if not _validate_session_ownership(session_id, current_user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: session not found or access denied"
            )

    async def generate_response() -> AsyncGenerator[str, None]:
        """生成流式响应"""
        nonlocal session_id, session_created

        try:
            # 1. 保存用户消息到数据库
            try:
                save_message_to_db(
                    session_id=session_id,
                    user_id=current_user_id,
                    role="user",
                    content=request_data.message
                )
            except Exception as e:
                logger.error(f"Failed to save user message: {e}")

            # 发送用户消息确认
            yield f"data: {json.dumps({'type': 'user_message', 'session_id': session_id, 'content': request_data.message})}\n\n"

            # 2. 获取历史消息（用于上下文）
            messages_history = _get_session_messages(session_id, limit=20)

            # 3. 网络搜索（如果启用）
            search_context = None
            if request_data.enable_search:
                try:
                    from backend.api.services.search_service import get_search_service

                    # 获取搜索服务
                    search_service = get_search_service(user_id=current_user_id)

                    # 1. 判断是否需要搜索
                    search_decision = search_service.should_search(
                        query=request_data.message,
                        user_id=current_user_id
                    )
                    logger.info(f"搜索决策: {search_decision}")

                    if not search_decision.get('need_search', False):
                        logger.info(f"无需搜索: {search_decision.get('reason', '')}")
                        # 不需要搜索，继续 LLM 生成
                        pass
                    else:
                        # 2. 需要搜索，发送搜索开始事件
                        yield f"data: {json.dumps({'type': 'search_start', 'session_id': session_id, 'message': '正在搜索网络信息...'})}\n\n"

                        # 3. 执行搜索
                        logger.info(f"开始执行搜索，enable_search={request_data.enable_search}")
                        search_result = search_service.execute_search(
                            query=request_data.message,
                            max_results=request_data.search_results,
                            force_search=False
                        )
                        logger.info(f"搜索结果: {search_result}")
                        # 检查搜索结果
                        if not search_result.get('sources'):
                            logger.warning(f"搜索结果为空: {search_result}")
                        else:
                            logger.info(f"搜索结果包含 {len(search_result.get('sources', []))} 条来源")

                        # 4. 格式化搜索结果为 LLM 友好的文本
                        if search_result.get('sources'):
                            formatted_results = _format_search_results_for_llm(search_result['sources'])
                            # 5. 发送搜索完成事件
                            yield f"data: {json.dumps({'type': 'search_complete', 'session_id': session_id, 'results': search_result['sources']})}\n\n"
                            # 6. 设置搜索上下文（保持原始数据结构，不覆盖为格式化字符串）
                            search_context = {
                                'query': search_result['optimized_query'],
                                'results': search_result['sources']
                            }
                        else:
                            search_context = None

                except ConnectionError as e:
                    logger.error(f"搜索连接失败: {e}")
                    yield f"data: {json.dumps({'type': 'search_error', 'session_id': session_id, 'message': '搜索服务暂时不可用，将尝试直接回答。'})}\n\n"
                except Exception as e:
                    logger.error(f"搜索失败: {e}", exc_info=True)
                    yield f"data: {json.dumps({'type': 'search_error', 'session_id': session_id, 'message': '搜索出错，将尝试直接回答。'})}\n\n"

            # 4. 初始化 LLM 并生成响应
            llm = LLMChat(model=request_data.model)

            full_response = ""
            full_thinking = ""

            # 准备增强的提示词（包含搜索上下文）
            enhanced_message = request_data.message
            if search_context and search_context.get('results'):
                # 将搜索结果作为系统上下文添加到消息中
                search_system_prompt = f"""
【网络搜索结果】
优化查询：{search_context.get('query', '')}

{formatted_results}

请基于以上搜索结果回答用户的问题。如果搜索结果中没有相关信息，请根据你的知识库回答，并在回答中说明哪些内容是基于搜索结果，哪些是基于你的知识。
"""
                # 将搜索上下文插入到消息历史开头
                messages_history_with_search = [
                    {"role": "system", "content": search_system_prompt}
                ] + messages_history[:-1]
            else:
                messages_history_with_search = messages_history[:-1]

            # 5. 流式生成响应
            async for chunk in llm.stream_chat_with_thinking(
                message=request_data.message,
                messages_history=messages_history_with_search
            ):
                if 'error' in chunk:
                    # 发送错误
                    error_data = {
                        'type': 'error',
                        'session_id': session_id,
                        'message': chunk['error']
                    }
                    yield f"data: {json.dumps(error_data)}\n\n"
                    return

                # 处理思考过程
                if 'thinking' in chunk:
                    thinking_text = chunk['thinking']
                    full_thinking += thinking_text

                    sse_data = {
                        'type': 'assistant_thinking',
                        'session_id': session_id,
                        'text': thinking_text,
                        'is_end': False
                    }
                    yield f"data: {json.dumps(sse_data)}\n\n"

                # 处理常规内容
                if 'content' in chunk:
                    content_text = chunk['content']
                    full_response += content_text

                    sse_data = {
                        'type': 'assistant_chunk',
                        'session_id': session_id,
                        'text': content_text,
                        'is_end': False
                    }
                    yield f"data: {json.dumps(sse_data)}\n\n"

            # 5. 处理 XML 格式的思考标签（如果有）
            if not full_thinking and full_response:
                from utils.llm_chat import extract_thinking_from_response
                thinking_from_xml, cleaned_response = extract_thinking_from_response(full_response)
                if thinking_from_xml:
                    full_thinking = thinking_from_xml
                    full_response = cleaned_response

            # 6. 保存助手消息到数据库
            try:
                save_message_to_db(
                    session_id=session_id,
                    user_id=current_user_id,
                    role="assistant",
                    content=full_response,
                    thinking=full_thinking if full_thinking else None,
                    model=request_data.model
                )
                # 更新会话时间戳
                update_session_timestamp(session_id)
            except Exception as e:
                logger.error(f"Failed to save assistant message: {e}")

            # 7. 发送结束标记
            end_data = {
                'type': 'assistant_end',
                'session_id': session_id,
                'full_text': full_response,
                'thinking': full_thinking if full_thinking else None,
                'is_end': True
            }
            yield f"data: {json.dumps(end_data)}\n\n"

        except Exception as e:
            logger.error(f"Error generating response: {e}")
            error_data = {
                'type': 'error',
                'session_id': session_id,
                'message': str(e)
            }
            yield f"data: {json.dumps(error_data)}\n\n"

    return StreamingResponse(
        generate_response(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # 禁用 Nginx 缓冲
        }
    )


# ===== 会话管理 =====

@router.get("/sessions", response_model=ChatSessionResponse)
async def list_sessions(
    page: int = 1,
    page_size: int = 20,
    current_user_id: int = Depends(get_current_user)
):
    """
    获取会话列表

    Args:
        page: 页码
        page_size: 每页数量
        current_user_id: 当前用户 ID

    Returns:
        会话列表
    """
    from utils.database import Database

    offset, limit = paginate(page, page_size)

    with Database.get_cursor() as cursor:
        # 查询总数
        cursor.execute(
            "SELECT COUNT(*) as total FROM chat_sessions WHERE user_id = %s",
            (current_user_id,)
        )
        total = cursor.fetchone()['total']

        # 使用单次查询获取会话和消息（优化 N+1 问题）
        cursor.execute("""
            SELECT
                s.id, s.user_id, s.title, s.model, s.created_at, s.updated_at,
                m.role as msg_role, m.content as msg_content, m.timestamp as msg_timestamp
            FROM chat_sessions s
            LEFT JOIN LATERAL (
                SELECT role, content, timestamp
                FROM chat_messages
                WHERE session_id = s.id
                ORDER BY timestamp DESC
                LIMIT 10
            ) m ON true
            WHERE s.user_id = %s
            ORDER BY s.updated_at DESC
            LIMIT %s OFFSET %s
        """, (current_user_id, limit, offset))

        rows = cursor.fetchall() or []

        logger.info("chat sessions listed", extra={"user_id": current_user_id, "total": total})

        if total == 0:
            return ChatSessionResponse(items=[], total=0)

        # 按会话分组消息
        from collections import defaultdict
        sessions_dict = defaultdict(lambda: {
            'id': None,
            'user_id': None,
            'title': None,
            'model': None,
            'created_at': None,
            'updated_at': None,
            'messages': []
        })

        for row in rows:
            session_id = row['id']
            sessions_dict[session_id]['id'] = row['id']
            sessions_dict[session_id]['user_id'] = row['user_id']
            sessions_dict[session_id]['title'] = row['title']
            sessions_dict[session_id]['model'] = row.get('model')
            sessions_dict[session_id]['created_at'] = row['created_at']
            sessions_dict[session_id]['updated_at'] = row['updated_at']

            # 添加消息（如果有）
            if row['msg_role']:
                sessions_dict[session_id]['messages'].append({
                    'role': row['msg_role'],
                    'content': row['msg_content'],
                    'timestamp': row['msg_timestamp']
                })

        # 构建响应
        session_list = []
        for session_data in sessions_dict.values():
            # 消息需要按时间正序排列
            messages = [
                ChatMessage(
                    role=msg['role'],
                    content=msg['content'],
                    timestamp=msg['timestamp']
                )
                for msg in reversed(session_data['messages'])
            ]

            session_list.append(ChatSession(
                id=session_data['id'],
                user_id=session_data['user_id'],
                title=session_data['title'],
                model=session_data.get('model'),
                messages=messages,
                created_at=session_data['created_at'],
                updated_at=session_data['updated_at']
            ))

    return ChatSessionResponse(items=session_list, total=total)


@router.post("/sessions", response_model=ChatSession, status_code=status.HTTP_201_CREATED)
async def create_session(
    request_data: Optional[ChatSessionCreate] = None,
    current_user_id: int = Depends(get_current_user)
):
    """
    创建新会话

    Args:
        request_data: 会话数据（可选）
        current_user_id: 当前用户 ID

    Returns:
        创建的会话
    """
    request_data = request_data or ChatSessionCreate()
    session_id = str(uuid.uuid4())

    from utils.database import Database

    with Database.get_cursor() as cursor:
        # 获取用户名
        cursor.execute("SELECT username FROM users WHERE id = %s", (current_user_id,))
        user = cursor.fetchone()
        username = user['username'] if user else 'unknown'

        cursor.execute("""
            INSERT INTO chat_sessions
            (id, user_id, username, title, model, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
            RETURNING id, user_id, username, title, model, created_at, updated_at
        """, (
            session_id,
            current_user_id,
            username,
            request_data.title,
            request_data.model
        ))

        session = cursor.fetchone()

    logger.info(f"Chat session created: id={session_id}")

    return ChatSession(
        id=session['id'],
        user_id=session['user_id'],
        title=session['title'],
        model=session.get('model'),
        messages=[],
        created_at=session['created_at'],
        updated_at=session['updated_at']
    )


@router.get("/sessions/{session_id}", response_model=ChatSession)
async def get_session(
    session_id: str,
    current_user_id: int = Depends(get_current_user)
):
    """
    获取会话详情

    Args:
        session_id: 会话 ID
        current_user_id: 当前用户 ID

    Returns:
        会话详情
    """
    from utils.database import Database

    with Database.get_cursor() as cursor:
        cursor.execute("""
            SELECT id, user_id, title, model, created_at, updated_at
            FROM chat_sessions
            WHERE id = %s AND user_id = %s
        """, (session_id, current_user_id))

        session = cursor.fetchone()

        if session is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )

        # 加载消息
        cursor.execute("""
            SELECT role, content, timestamp
            FROM chat_messages
            WHERE session_id = %s
            ORDER BY timestamp ASC
        """, (session_id,))

        messages = [
            ChatMessage(
                role=msg['role'],
                content=msg['content'],
                timestamp=msg['timestamp']
            )
            for msg in cursor.fetchall()
        ]

    return ChatSession(
        id=session['id'],
        user_id=session['user_id'],
        title=session['title'],
        model=session.get('model'),
        messages=messages,
        created_at=session['created_at'],
        updated_at=session['updated_at']
    )


@router.put("/sessions/{session_id}", response_model=ChatSession)
async def update_session(
    session_id: str,
    request_data: ChatSessionUpdate,
    current_user_id: int = Depends(get_current_user)
):
    """
    更新会话

    Args:
        session_id: 会话 ID
        request_data: 更新数据
        current_user_id: 当前用户 ID

    Returns:
        更新后的会话
    """
    from utils.database import Database

    update_fields = []
    params = []

    if request_data.title is not None:
        update_fields.append("title = %s")
        params.append(request_data.title)

    if request_data.model is not None:
        update_fields.append("model = %s")
        params.append(request_data.model)

    if not update_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update"
        )

    update_fields.append("updated_at = NOW()")
    params.extend([session_id, current_user_id])

    with Database.get_cursor() as cursor:
        cursor.execute(f"""
            UPDATE chat_sessions
            SET {', '.join(update_fields)}
            WHERE id = %s AND user_id = %s
            RETURNING id, user_id, title, model, created_at, updated_at
        """, params)

        session = cursor.fetchone()

        if session is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )

    logger.info(f"Chat session updated: id={session_id}")

    return ChatSession(
        id=session['id'],
        user_id=session['user_id'],
        title=session['title'],
        model=session.get('model'),
        messages=[],
        created_at=session['created_at'],
        updated_at=session['updated_at']
    )


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: str,
    current_user_id: int = Depends(get_current_user)
):
    """
    删除会话

    Args:
        session_id: 会话 ID
        current_user_id: 当前用户 ID
    """
    from utils.database import Database

    with Database.get_cursor() as cursor:
        # 先删除消息
        cursor.execute(
            "DELETE FROM chat_messages WHERE session_id = %s",
            (session_id,)
        )

        # 再删除会话
        cursor.execute(
            "DELETE FROM chat_sessions WHERE id = %s AND user_id = %s",
            (session_id, current_user_id)
        )

        if cursor.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )

    logger.info(f"Chat session deleted: id={session_id}")
