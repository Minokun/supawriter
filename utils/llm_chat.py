import openai
import time
import json
import re
import uuid
import logging
from typing import AsyncGenerator, Optional, Dict, Any, List

openai.log_level = "warning"

# 需要触发备用模型的错误关键词
FALLBACK_ERROR_KEYWORDS = [
    'security_audit_fail',  # 内容审核失败
    'security_error',       # 安全错误
    '违规',                  # 违规内容
    'content_filter',       # 内容过滤
    'content_policy',       # 内容策略
    'moderation',           # 内容审核
    'rate_limit',           # 速率限制
    'quota_exceeded',       # 配额超限
    '429',                  # Too Many Requests
    '403',                  # Forbidden
]

# 模型特定的 temperature 配置
MODEL_TEMPERATURE_CONFIG = {
    'kimi-k2.5': 1.0,  # kimi-k2.5 模型要求固定使用 1.0
}

# 默认 temperature 值
DEFAULT_TEMPERATURE = 0.7


def _get_db_llm_providers() -> Dict[str, Dict[str, Any]]:
    """
    从数据库获取所有 LLM 提供商配置

    Returns:
        Dict: {provider_id: {api_key, base_url, models: [...]}}
    """
    try:
        from backend.api.services.tier_service import TierService
        return TierService.get_all_provider_credentials()
    except Exception as e:
        logging.error(f"从数据库获取 LLM 提供商配置失败: {e}")
        return {}


def _get_db_provider_credentials(provider: str) -> tuple:
    """
    从数据库获取单个提供商的凭据

    Args:
        provider: 提供商名称

    Returns:
        tuple: (api_key, base_url, models) 或 (None, None, None)
    """
    try:
        from backend.api.services.tier_service import TierService
        credentials = TierService.get_provider_credentials(provider)
        if credentials:
            return (
                credentials.get('api_key'),
                credentials.get('base_url'),
                credentials.get('models', [])
            )
    except Exception as e:
        logging.debug(f"从数据库获取 {provider} 凭据失败: {e}")
    return None, None, None


def _find_provider_by_model(model_name: str) -> Optional[str]:
    """
    根据模型名称查找对应的提供商

    Args:
        model_name: 模型名称

    Returns:
        provider_id 或 None
    """
    providers = _get_db_llm_providers()
    for provider_id, config in providers.items():
        models = config.get('models', [])
        for model in models:
            if isinstance(model, dict):
                if model.get('name') == model_name:
                    return provider_id
            elif model == model_name:
                return provider_id
    return None


def _get_fallback_config():
    """
    获取备用模型配置
    Returns:
        dict or None: 备用模型配置，如果未启用则返回 None
    """
    try:
        from utils.config_manager import get_config
        config = get_config()
        model_settings = config.get('global_model_settings', {})
        fallback = model_settings.get('fallback', {})
        if fallback.get('enabled') and fallback.get('provider') and fallback.get('model_name'):
            return fallback
    except Exception as e:
        logging.debug(f"获取备用模型配置失败: {e}")
    return None


def _should_use_fallback(error: Exception) -> bool:
    """
    判断是否应该使用备用模型
    Args:
        error: 捕获的异常
    Returns:
        bool: 是否应该切换到备用模型
    """
    error_str = str(error).lower()
    for keyword in FALLBACK_ERROR_KEYWORDS:
        if keyword.lower() in error_str:
            return True
    return False


def _call_llm(client, model_name, system_prompt, prompt, max_tokens=8192):
    """
    调用 LLM API 的内部函数
    :param max_tokens: 最大生成token数，默认8192以支持长文本生成
    """
    # 根据模型名称获取对应的 temperature 值
    temperature = MODEL_TEMPERATURE_CONFIG.get(model_name, DEFAULT_TEMPERATURE)

    try:
        # 首先尝试使用system role
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            temperature=temperature,
            stream=False,
            extra_body={"thinking": {"type": "disabled"}}
        )
        return response.choices[0].message.content
    except Exception as e:
        # 检查是否是system role不支持的错误
        if "'messages[0].role' does not support 'system'" in str(e) or "role" in str(e):
            # 如果是system role不支持，则将system prompt合并到user prompt中
            combined_prompt = f"{system_prompt}\n\n{prompt}"
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "user", "content": combined_prompt},
                ],
                temperature=temperature,
                stream=False,
                extra_body={"thinking": {"type": "disabled"}}
            )
            return response.choices[0].message.content
        else:
            raise


def _get_provider_credentials(provider: str) -> tuple:
    """
    获取提供商的凭据（API key 和 base URL）

    仅从数据库获取

    Args:
        provider: 提供商名称

    Returns:
        tuple: (api_key, base_url)

    Raises:
        ValueError: 如果找不到配置
    """
    api_key, base_url, _ = _get_db_provider_credentials(provider)

    if not api_key:
        raise ValueError(f"找不到提供商 {provider} 的配置，请在系统设置中配置 API Key")

    return api_key, base_url


def chat(prompt, system_prompt, model_type='deepseek', model_name='deepseek-chat', max_retries=3, max_tokens=8192):
    """
    与LLM模型进行对话，支持备用模型自动切换
    :param prompt: 用户提示词
    :param system_prompt: 系统提示词
    :param model_type: 模型类型
    :param model_name: 模型名称
    :param max_retries: 最大重试次数
    :param max_tokens: 最大生成token数，默认8192以支持长文本生成
    :return: 模型回复内容
    """
    retries = 0
    last_error = None
    used_fallback = False

    while retries < max_retries:
        try:
            # 获取凭据（从数据库）
            api_key, base_url = _get_provider_credentials(model_type)

            # 创建API客户端
            client = openai.OpenAI(api_key=api_key, base_url=base_url)

            # 调用 LLM
            return _call_llm(client, model_name, system_prompt, prompt, max_tokens=max_tokens)

        except openai.APIError as e:
            last_error = e
            logging.error(f"API错误 (尝试 {retries+1}/{max_retries}): {str(e)}")
        except openai.APIConnectionError as e:
            last_error = e
            logging.error(f"API连接错误 (尝试 {retries+1}/{max_retries}): {str(e)}")
        except openai.RateLimitError as e:
            last_error = e
            logging.error(f"API速率限制错误 (尝试 {retries+1}/{max_retries}): {str(e)}")
            # 速率限制错误可能需要更长的等待时间
            time.sleep(2 * (retries + 1))
        except json.JSONDecodeError as e:
            last_error = e
            logging.error(f"JSON解析错误 (尝试 {retries+1}/{max_retries}): {str(e)}")
        except Exception as e:
            last_error = e
            logging.error(f"未知错误 (尝试 {retries+1}/{max_retries}): {str(e)}")

        # 检查是否应该使用备用模型（在第一次失败后检查）
        if retries == 0 and not used_fallback and _should_use_fallback(last_error):
            fallback_config = _get_fallback_config()
            if fallback_config:
                fallback_provider = fallback_config['provider']
                fallback_model = fallback_config['model_name']

                # 确保备用模型与当前模型不同
                if fallback_provider != model_type or fallback_model != model_name:
                    logging.warning(f"检测到需要切换备用模型的错误，尝试使用备用模型: {fallback_provider}/{fallback_model}")

                    try:
                        # 获取备用模型凭据
                        fallback_api_key, fallback_base_url = _get_provider_credentials(fallback_provider)
                        # 使用备用模型重试
                        fallback_client = openai.OpenAI(
                            api_key=fallback_api_key,
                            base_url=fallback_base_url
                        )
                        result = _call_llm(fallback_client, fallback_model, system_prompt, prompt, max_tokens=max_tokens)
                        logging.info(f"备用模型调用成功: {fallback_provider}/{fallback_model}")
                        return result
                    except Exception as fallback_error:
                        logging.error(f"备用模型也失败了: {str(fallback_error)}")
                        used_fallback = True
                        # 继续原来的重试逻辑

        # 增加重试次数并等待
        retries += 1
        if retries < max_retries:
            # 指数退避策略
            time.sleep(1 * retries)

    # 所有重试都失败了，抛出异常
    error_message = f"LLM模型连接失败: {str(last_error)}"
    raise ConnectionError(error_message)


# =============================================================================
# LLMChat 类：支持流式响应和思考过程的聊天封装
# =============================================================================

class LLMChat:
    """
    LLM 聊天客户端类
    支持流式响应、思考过程提取、模型配置等
    所有配置从数据库 global_llm_providers 表获取
    """

    def __init__(self, model: Optional[str] = None):
        """
        初始化 LLM 客户端

        Args:
            model: 模型标识符 (格式: "provider/model_name" 或仅 "model_name")
                   如果为 None，则从全局配置获取
        """
        self.model = model
        self.client, self.model_type, self.model_name = self._init_client()

    def _init_client(self) -> tuple:
        """
        从数据库初始化客户端

        Returns:
            tuple: (openai_client, provider, model_name)
        """
        from utils.config_manager import get_config

        # 解析模型参数
        provider = None
        model_name = None

        if self.model:
            # 支持多种分隔符: "provider/model_name" 或 "provider:model_name"
            if '/' in self.model:
                provider, model_name = self.model.split('/', 1)
            elif ':' in self.model:
                provider, model_name = self.model.split(':', 1)
            else:
                # 仅模型名称，需要查找对应的 provider
                provider = _find_provider_by_model(self.model)
                if provider:
                    model_name = self.model

        # 如果没有从模型参数解析出来，从全局配置获取
        if not provider or not model_name:
            try:
                config = get_config()
                global_settings = config.get('global_model_settings', {})
                if global_settings:
                    provider = global_settings.get('provider')
                    model_name = global_settings.get('model_name')
            except Exception as e:
                logging.debug(f"获取全局配置失败: {e}")

        # 仍然没有的话，使用第一个可用模型
        if not provider or not model_name:
            providers = _get_db_llm_providers()
            if providers:
                provider = list(providers.keys())[0]
                models = providers[provider].get('models', [])
                if models:
                    first_model = models[0]
                    model_name = first_model.get('name') if isinstance(first_model, dict) else first_model

        if not provider or not model_name:
            raise ValueError("没有可用的 LLM 提供商配置，请在系统设置中配置 API Key")

        # 从数据库获取凭据
        api_key, base_url, _ = _get_db_provider_credentials(provider)

        if not api_key:
            raise ValueError(f"提供商 {provider} 没有配置 API Key，请在系统设置中配置")

        if not base_url:
            raise ValueError(f"提供商 {provider} 没有配置 base_url")

        # 创建 OpenAI 客户端
        client = openai.OpenAI(api_key=api_key, base_url=base_url)

        logging.info(f"LLMChat 初始化: {provider}/{model_name}")

        return client, provider, model_name

    async def stream_chat_with_thinking(
        self,
        message: str,
        messages_history: Optional[list] = None
    ) -> AsyncGenerator[Dict[str, str], None]:
        """
        流式聊天，支持思考过程

        Args:
            message: 用户消息
            messages_history: 历史消息列表（可选）

        Yields:
            dict: 包含 'content' 和/或 'thinking' 的字典
        """
        import asyncio

        # 构建消息列表
        messages = messages_history or []
        messages.append({"role": "user", "content": message})

        # 确定最大 token 数
        max_tokens = 8000 if self.model_type == 'openai' else 8192

        # 获取 temperature
        temperature = MODEL_TEMPERATURE_CONFIG.get(self.model_name, DEFAULT_TEMPERATURE)

        try:
            # 创建流式请求
            stream = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=temperature,
                stream=True,
                max_tokens=max_tokens
            )

            # 使用 asyncio.to_thread 将同步迭代器转换为异步，避免阻塞事件循环
            # 创建一个哨兵对象来标记迭代结束
            sentinel = object()
            chunk_count = 0

            while True:
                # 在线程池中运行同步 __next__，释放事件循环
                # 使用哨兵模式避免 StopIteration 异常传播到 async
                chunk = await asyncio.to_thread(next, stream, sentinel)

                if chunk is sentinel:
                    logging.info(f"[流式] 完成，共收到 {chunk_count} 个 chunks")
                    break

                chunk_count += 1

                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta

                    # 检查 reasoning_content（思考过程，适用于 deepseek-r1, o1 等模型）
                    if hasattr(delta, 'reasoning_content') and delta.reasoning_content:
                        yield {'thinking': delta.reasoning_content}

                    # 处理常规内容
                    if delta.content is not None:
                        yield {'content': delta.content}

        except Exception as e:
            logging.error(f"流式聊天错误: {e}")
            yield {'error': str(e)}

    async def stream_chat_with_search_context(
        self,
        message: str,
        messages_history: Optional[list] = None,
        search_context: Optional[str] = None
    ) -> AsyncGenerator[Dict[str, str], None]:
        """
        流式聊天，支持搜索上下文

        Args:
            message: 用户消息
            messages_history: 历史消息列表（可选）
            search_context: 搜索上下文（可选），格式化为 LLM 友好的文本

        Yields:
            dict: 包含 'content' 和/或 'thinking' 的字典
        """
        import asyncio

        # 构建消息列表
        messages = messages_history or []

        # 如果有搜索上下文，添加为系统消息
        if search_context:
            messages.append({
                "role": "system",
                "content": search_context
            })

        messages.append({"role": "user", "content": message})

        # 确定最大 token 数
        max_tokens = 8000 if self.model_type == 'openai' else 8192

        # 获取 temperature
        temperature = MODEL_TEMPERATURE_CONFIG.get(self.model_name, DEFAULT_TEMPERATURE)

        try:
            # 创建流式请求
            stream = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=temperature,
                stream=True,
                max_tokens=max_tokens
            )

            # 使用 asyncio.to_thread 将同步迭代器转换为异步，避免阻塞事件循环
            # 创建一个哨兵对象来标记迭代结束
            sentinel = object()
            chunk_count = 0

            while True:
                # 在线程池中运行同步 __next__，释放事件循环
                # 使用哨兵模式避免 StopIteration 异常传播到 async
                chunk = await asyncio.to_thread(next, stream, sentinel)

                if chunk is sentinel:
                    logging.info(f"[流式-搜索上下文] 完成，共收到 {chunk_count} 个 chunks")
                    break

                chunk_count += 1

                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta

                    # 检查 reasoning_content（思考过程，适用于 deepseek-r1, o1 等模型）
                    if hasattr(delta, 'reasoning_content') and delta.reasoning_content:
                        yield {'thinking': delta.reasoning_content}

                    # 处理常规内容
                    if delta.content is not None:
                        yield {'content': delta.content}

        except Exception as e:
            logging.error(f"流式聊天错误: {e}")
            yield {'error': str(e)}

    @staticmethod
    def extract_thinking_from_response(response: str) -> tuple[str, str]:
        """
        从响应中提取思考内容（处理 XML 格式的思考标签）

        Args:
            response: 完整的响应文本

        Returns:
            tuple: (thinking_content, cleaned_response)
        """
        think_patterns = [
            (r'```thinking(.*?)```', 'code_block'),
            (r'<thinking>(.*?)</thinking>', 'xml'),
            (r'<thought>(.*?)</thought>', 'xml')
        ]

        thinking_parts = []
        cleaned_response = response

        for pattern, tag_type in think_patterns:
            matches = re.findall(pattern, response, re.DOTALL)
            if matches:
                thinking_parts.extend(matches)
                cleaned_response = re.sub(pattern, '', cleaned_response, flags=re.DOTALL).strip()
                break

        thinking = '\n\n'.join(thinking_parts) if thinking_parts else None
        return thinking, cleaned_response.strip()


# =============================================================================
# 独立的思考内容提取函数（可在不创建 LLMChat 实例的情况下使用）
# =============================================================================

def extract_thinking_from_response(response: str) -> tuple[str, str]:
    """
    从响应中提取思考内容（处理 XML 格式的思考标签）
    这是 LLMChat.extract_thinking_from_response 的独立版本

    Args:
        response: 完整的响应文本

    Returns:
        tuple: (thinking_content, cleaned_response)
    """
    return LLMChat.extract_thinking_from_response(response)


# =============================================================================
# 消息持久化辅助函数
# =============================================================================

# 消息长度限制（字符数）
MAX_MESSAGE_CONTENT_LENGTH = 100000  # 100K 字符
MAX_THINKING_CONTENT_LENGTH = 500000  # 500K 字符（思考过程可能很长）


def save_message_to_db(
    session_id: str,
    user_id: int,
    role: str,
    content: str,
    thinking: Optional[str] = None,
    model: Optional[str] = None
) -> str:
    """
    保存单条消息到数据库

    Args:
        session_id: 会话 ID
        user_id: 用户 ID
        role: 消息角色 ('user' | 'assistant' | 'system')
        content: 消息内容
        thinking: 可选的思考过程
        model: 可选的模型名称

    Returns:
        str: 新创建的消息 ID

    Raises:
        ValueError: 如果消息内容超过长度限制
        Exception: 如果保存失败，异常会传递给调用者处理
    """
    from utils.database import Database

    # 验证消息长度
    if len(content) > MAX_MESSAGE_CONTENT_LENGTH:
        raise ValueError(
            f"消息内容过长：{len(content)} 字符（最大允许 {MAX_MESSAGE_CONTENT_LENGTH} 字符）"
        )

    if thinking and len(thinking) > MAX_THINKING_CONTENT_LENGTH:
        raise ValueError(
            f"思考过程过长：{len(thinking)} 字符（最大允许 {MAX_THINKING_CONTENT_LENGTH} 字符）"
        )

    message_id = str(uuid.uuid4())

    with Database.get_cursor() as cursor:
        cursor.execute("""
            INSERT INTO chat_messages (id, session_id, user_id, role, content, thinking, model)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (message_id, session_id, user_id, role, content, thinking, model))

    logging.debug(f"消息已保存: {message_id}, role={role}")
    return message_id


def update_session_timestamp(session_id: str) -> bool:
    """
    更新会话时间戳（触发器会自动设置 updated_at）

    Args:
        session_id: 会话 ID

    Returns:
        bool: 是否成功
    """
    from utils.database import Database

    try:
        with Database.get_cursor() as cursor:
            cursor.execute("""
                UPDATE chat_sessions
                SET updated_at = NOW()
                WHERE id = %s
            """, (session_id,))

        return True

    except Exception as e:
        logging.error(f"更新会话时间戳失败: {e}")
        return False


if __name__ == '__main__':
    prompt = '请叫我如何才能哄女孩子开心'
    system_prompt = "你是一个来自台湾的知心大姐姐，会用最温柔最贴心最绿茶的话和我聊天。"
    response = chat(prompt, system_prompt, model_type='deepseek', model_name='deepseek-chat')
    print(response)
