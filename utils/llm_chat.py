import openai
import pyglet
import time
import json
from settings import LLM_MODEL
import logging

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


def _call_llm(client, model_name, system_prompt, prompt):
    """
    调用 LLM API 的内部函数
    """
    try:
        # 首先尝试使用system role
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
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
                temperature=0.3,
                stream=False,
                extra_body={"thinking": {"type": "disabled"}}
            )
            return response.choices[0].message.content
        else:
            raise


def chat(prompt, system_prompt, model_type='deepseek', model_name='deepseek-chat', max_retries=3):
    """
    与LLM模型进行对话，支持备用模型自动切换
    :param prompt: 用户提示词
    :param system_prompt: 系统提示词
    :param model_type: 模型类型
    :param model_name: 模型名称
    :param max_retries: 最大重试次数
    :return: 模型回复内容
    """
    retries = 0
    last_error = None
    used_fallback = False
    
    while retries < max_retries:
        try:
            # 检查模型配置是否存在
            if model_type not in LLM_MODEL:
                available_models = ", ".join(LLM_MODEL.keys())
                raise ValueError(f"模型类型 '{model_type}' 不存在。可用的模型类型: {available_models}")
            
            # 创建API客户端
            client = openai.OpenAI(
                api_key=LLM_MODEL[model_type]['api_key'], 
                base_url=LLM_MODEL[model_type]['base_url']
            )
            
            # 调用 LLM
            return _call_llm(client, model_name, system_prompt, prompt)
            
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
                        # 使用备用模型重试
                        fallback_client = openai.OpenAI(
                            api_key=LLM_MODEL[fallback_provider]['api_key'],
                            base_url=LLM_MODEL[fallback_provider]['base_url']
                        )
                        result = _call_llm(fallback_client, fallback_model, system_prompt, prompt)
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

if __name__ == '__main__':
    prompt = '请叫我如何才能哄女孩子开心'
    system_prompt = "你是一个来自台湾的知心大姐姐，会用最温柔最贴心最绿茶的话和我聊天。"
    response = chat(prompt, system_prompt, model_type='xinference', model_name='qwen2.5-instruct')
    print(response)