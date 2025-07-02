import requests
import base64
import os
import json
import logging
from typing import Dict, Optional, Union, Any

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# API配置
BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
MODEL = "qwen-vl-plus-2025-01-25"
API_KEY = "sk-cabc155d7d094825b2b1f0e9ffea35dd"

# 示例提示词，与gemma3_client.py中的类似
sample_prompt = """
分析这张图片。如果它是宣传图片、广告、图标或任何其他类型不传达特定信息的图片，请将其状态标记为已删除，将`is_deleted`设置为`true`。
对于其他图片，请用中文详细描述图片内容，填入`describe`字段。然后，将其与主题'{theme}'进行比较，确定相关性。如果相关，将`is_related`标记为`true`；否则，标记为`false`。

仅以下面的JSON格式回复(使用true/false):
{
    "is_deleted": false,
    "describe": "用中文描述图片",
    "is_related": false
}
"""

def call_qwen_vl_api(prompt: str = sample_prompt, 
                     image_path: str = None, 
                     image_url: str = None, 
                     image_content: bytes = None) -> Dict[str, Any]:
    """
    调用阿里云DashScope的Qwen-VL多模态API，处理图像和文本提示。
    图像可以通过以下三种方式之一提供：
    1. 本地文件路径
    2. 图像URL
    3. 已获取的原始二进制内容

    Args:
        prompt: 发送给模型的文本提示。
        image_path: 本地图像文件的路径（可选）。
        image_url: 要下载的图像的URL（可选）。
        image_content: 已获取的原始二进制图像内容（可选）。

    Returns:
        来自API响应的解析后的JSON内容，如果发生错误则返回None。
    """
    
    # 检查是否提供了恰好一个图像源
    sources_provided = sum(x is not None for x in [image_path, image_url, image_content])
    if sources_provided == 0:
        logger.error("错误：必须提供image_path、image_url或image_content之一")
        return None
    elif sources_provided > 1:
        logger.warning("警告：提供了多个图像源。按以下顺序使用第一个可用的：image_path、image_url、image_content")
    
    # 获取图像内容作为base64
    try:
        if image_path is not None:
            # 从本地文件加载
            with open(image_path, 'rb') as f:
                image_base64 = base64.b64encode(f.read()).decode('utf-8')
        elif image_url is not None:
            # 从URL下载
            response = requests.get(image_url, stream=True)
            response.raise_for_status()
            image_base64 = base64.b64encode(response.content).decode('utf-8')
        elif image_content is not None:
            # 使用已获取的内容
            image_base64 = base64.b64encode(image_content).decode('utf-8')
    except Exception as e:
        logger.error(f"处理图像时出错: {e}")
        return None

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }

    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "system",
                "content": "你是一个专门从事图像分析和描述的助手。彻底分析图像并提供详细描述。始终使用有效的、格式正确的JSON进行响应。在回复中避免使用markdown格式。如果被要求评估或分类图像，请在评估中保持精确和一致。专注于图像中存在的视觉元素、文本内容和上下文信息。"
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_base64}"
                        }
                    },
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
            }
        ],
        "max_tokens": 5000
    }

    try:
        response = requests.post(f"{BASE_URL}/chat/completions", headers=headers, json=payload)
        response.raise_for_status()  # 对HTTP错误（4xx或5xx）引发异常
        
        # 获取原始API响应
        api_response = response.json()
        
        # 从响应中提取内容
        if api_response and 'choices' in api_response and len(api_response['choices']) > 0:
            content = api_response['choices'][0]['message']['content']
            logger.debug(f"原始API响应内容: {content}")
            
            # 清理内容，如果它被markdown代码块包装或有额外的空白
            content = content.strip()
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0].strip()
            elif '```' in content:
                content = content.split('```')[1].split('```')[0].strip()
            
            # 处理可能破坏JSON解析的前导/尾随字符
            # 删除第一个{之前和最后一个}之后的任何非JSON文本
            try:
                start_idx = content.index('{')
                end_idx = content.rindex('}') + 1
                content = content[start_idx:end_idx]
            except ValueError:
                logger.error("在内容中找不到有效的JSON标记")
            
            # 尝试解析JSON内容
            try:
                result = json.loads(content)
                logger.debug(f"成功解析JSON: {result}")
                return result
            except json.JSONDecodeError as e:
                logger.error(f"无法从API响应解析JSON: {e}")
                # 尝试更宽松的方法 - 处理Python样式的布尔值和引号
                try:
                    import re
                    # 将Python True/False替换为JSON true/false
                    content = re.sub(r"True", "true", content)
                    content = re.sub(r"False", "false", content)
                    # 将'true'和'false'替换为true和false（没有引号）
                    content = re.sub(r"'true'", "true", content)
                    content = re.sub(r"'false'", "false", content)
                    # 将剩余的单引号替换为双引号
                    content = content.replace("'", '"')
                    result = json.loads(content)
                    logger.info(f"清理后成功解析JSON: {result}")
                    return result
                except json.JSONDecodeError as e2:
                    logger.error(f"清理后仍无法解析JSON: {e2}")
                    return {"error": "JSON解析失败", "raw_content": content}
        
        logger.error("无效或不完整的API响应结构")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"调用Qwen-VL API时出错: {e}")
        return None

def process_image(image_url: str, theme: str = "") -> Dict[str, Any]:
    """
    处理单个图像并返回分析结果
    
    Args:
        image_url: 图像的URL
        theme: 用于相关性比较的主题
        
    Returns:
        包含图像分析结果的字典
    """
    # 构建提示词，替换主题
    prompt = sample_prompt.replace("{theme}", theme) if theme else sample_prompt
    
    # 调用Qwen-VL API
    try:
        result = call_qwen_vl_api(prompt=prompt, image_url=image_url)
        
        if result:
            # 确保结果包含所需字段
            if not isinstance(result, dict):
                logger.error(f"API返回了非字典结果: {result}")
                return None
                
            # 确保结果包含必要的字段
            if "describe" not in result:
                result["describe"] = ""
            if "is_related" not in result:
                result["is_related"] = False
            if "is_deleted" not in result:
                result["is_deleted"] = False
                
            # 添加图像URL到结果中
            result["image_url"] = image_url
            return result
        else:
            logger.warning(f"处理图像时没有返回结果: {image_url}")
            return None
    except Exception as e:
        logger.error(f"处理图像时出错: {e}")
        return None

# 测试代码
if __name__ == "__main__":
    # 测试图像URL
    test_image_url = "https://img-blog.csdnimg.cn/img_convert/9f9ea5e5338cbbfda46b8bf2c78d7ef6.png"
    test_theme = "人工智能"
    
    # 处理图像
    result = process_image(test_image_url, test_theme)
    
    # 打印结果
    if result:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("处理图像失败")
