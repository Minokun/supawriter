import base64
import os, sys
# 添加当前项目路径到sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json
import logging
from openai import OpenAI
from zai import ZhipuAiClient
from settings import PROCESS_CONFIG, PROCESS_IMAGE_TYPE
import requests

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

if PROCESS_IMAGE_TYPE == "qwen":
    client = OpenAI(
        api_key=PROCESS_CONFIG['qwen']['api_key'],
        base_url=PROCESS_CONFIG['qwen']['base_url'],
    )
else:
    client = ZhipuAiClient(
        api_key=PROCESS_CONFIG['glm']['api_key']
    )

# 示例提示词，与gemma3_client.py中的类似
sample_prompt = """
用中文详细描述图片内容作为后续文章的图片说明，包括图片关键字
"""

def openai_ali(prompt=sample_prompt, image_path: str = None, image_url: str = None, image_content: bytes = None):
    
    # 准备图像数据
    if image_path:
        # 从本地文件加载图像
        with open(image_path, "rb") as f:
            image_data = f.read()
        image_base64 = base64.b64encode(image_data).decode("utf-8")
        image_url_with_prefix = f"data:image/jpeg;base64,{image_base64}"
    elif image_url:
        image_url_with_prefix = image_url
    elif image_content:
        # 使用已提供的图像内容
        image_base64 = base64.b64encode(image_content).decode("utf-8")
        image_url_with_prefix = f"data:image/jpeg;base64,{image_base64}"
    else:
        raise ValueError("必须提供image_path、image_url或image_content")
    
    completion = client.chat.completions.create(
        model=PROCESS_CONFIG[PROCESS_IMAGE_TYPE]['model'],
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": image_url_with_prefix
                        }
                    }
                ]
            }
        ]
    )
    try:
        content_text = completion.choices[0].message.content
        
        res_content = {}
        res_content['describe'] = content_text
        if image_url:
            res_content["image_url"] = image_url
            
        return res_content
    except Exception as e:
        logger.error(f"处理API响应时出错: {e}")
        return {
            "error": str(e),
            "describe": "图像处理失败",
            "image_url": image_url
        }

def process_image(prompt=sample_prompt, image_path: str = None, image_url: str = None, image_content: bytes = None):
    return openai_ali(prompt, image_path, image_url, image_content)
    
# 已移除call_gemma3_api函数，统一使用qwen模型处理图像


# 测试代码
if __name__ == "__main__":
    # 测试图像URL - 使用更可靠的公共图像源
    test_image_url = "https://www.baidu.com/img/PCtm_d9c8750bed0b3c7d089fa7d55720d6cf.png"
    # 处理图像
    print("处理图像并获取分析结果...")
    result = process_image(prompt=sample_prompt, image_url=test_image_url)
    
    # 打印结果
    if result:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("处理图像失败")