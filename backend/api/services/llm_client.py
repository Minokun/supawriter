# -*- coding: utf-8 -*-
"""
LLM客户端服务 - 用于评分功能调用LLM API
"""

import json
import logging
from typing import Optional

# 使用现有的llm_chat模块
try:
    from utils.llm_chat import chat
except ImportError:
    chat = None

logger = logging.getLogger(__name__)


class LLMClient:
    """LLM客户端"""

    def __init__(self):
        self._chat = chat

    async def chat_completion(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model_type: str = 'deepseek',
        model_name: str = 'deepseek-chat',
        temperature: float = 0.7,
        max_retries: int = 3
    ) -> str:
        """
        调用LLM完成对话

        Args:
            prompt: 用户提示词
            system_prompt: 系统提示词
            model_type: 模型类型
            model_name: 模型名称
            temperature: 温度参数
            max_retries: 最大重试次数

        Returns:
            LLM响应文本
        """
        if not self._chat:
            logger.warning("LLM聊天模块不可用，返回默认评分")
            return self._get_default_response()

        try:
            response = await self._chat(
                prompt=prompt,
                system_prompt=system_prompt,
                model_type=model_type,
                model_name=model_name,
                max_retries=max_retries
            )

            # 清理响应，提取JSON部分
            json_response = self._extract_json(response)

            if json_response:
                return json_response
            else:
                # 如果无法提取JSON，返回原始响应
                return response

        except Exception as e:
            logger.error(f"LLM调用失败: {e}")
            return self._get_default_response()

    def _get_default_response(self) -> str:
        """获取默认JSON响应"""
        return json.dumps({
            "score": 70,
            "suggestions": ["LLM分析暂时不可用"]
        }, ensure_ascii=False)

    def _extract_json(self, response: str) -> Optional[str]:
        """
        从响应中提取JSON部分

        尝试以下格式：
        1. 纯JSON格式
        2. 包含```json ... ```标记
        3. 包含{ ... }格式的代码块
        """
        if not response:
            return None

        response = response.strip()

        # 尝试1: 检查是否是纯JSON
        try:
            json.loads(response)
            return response
        except json.JSONDecodeError:
            pass

        # 尝试2: 提取 ```json ... ``` 标记
        if '```json' in response or '```' in response:
            # 提取第一个代码块
            start_marker = '```json' if '```json' in response else '```'
            start_idx = response.find(start_marker)
            if start_idx != -1:
                start_idx += len(start_marker)
                end_idx = response.find('```', start_idx)
                if end_idx != -1:
                    code_block = response[start_idx:end_idx].strip()
                    try:
                        json.loads(code_block)
                        return code_block
                    except json.JSONDecodeError:
                        pass

        # 尝试3: 提取 { ... } 格式
        if '{' in response and '}' in response:
            first_brace = response.find('{')
            last_brace = response.rfind('}')
            if first_brace != -1 and last_brace != -1:
                candidate = response[first_brace:last_brace + 1]
                try:
                    json.loads(candidate)
                    return candidate
                except json.JSONDecodeError:
                    pass

        return None
