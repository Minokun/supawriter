import base64
import os, sys
# 添加当前项目路径到sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json
import logging
from openai import OpenAI
from settings import OPENAI_VL_MODEL, OPENAI_VL_API_KEY, OPENAI_VL_BASE_URL, PROCESS_IMAGE_TYPE
import requests

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# API配置
BASE_URL = OPENAI_VL_BASE_URL
MODEL = OPENAI_VL_MODEL
API_KEY = OPENAI_VL_API_KEY

# 示例提示词，与gemma3_client.py中的类似
sample_prompt = """
分析这张图片。如果它是宣传图片、广告、图标或任何其他类型不传达特定信息的图片，请将其状态标记为已删除，将`is_deleted`设置为`true`。
对于其他图片，请用中文详细描述图片内容，填入`describe`字段。然后，将其与主题'{}'进行比较，确定相关性。如果相关，将`is_related`标记为`true`；否则，标记为`false`。

仅以下面的JSON格式回复(使用true/false):
{{
    "is_deleted": false,
    "describe": "用中文详细描述图片内容作为后续文章的图片说明",
    "is_related": false
}}
"""

def openai_ali(prompt=sample_prompt, image_path: str = None, image_url: str = None, image_content: bytes = None, theme: str = ""):
    client = OpenAI(
        api_key=API_KEY,
        base_url=BASE_URL,
    )
    
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
        model=MODEL,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt.format(theme)
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
        # 直接从响应对象中提取内容
        content_text = completion.choices[0].message.content
        print(f"API响应内容: {content_text}")
        
        # 处理可能的markdown格式的JSON
        if content_text.strip().startswith('```') and '```' in content_text:
            # 从 markdown 代码块中提取JSON
            json_content = content_text.split('```', 2)[1]
            if json_content.startswith('json'):
                json_content = json_content[4:].strip()
            else:
                json_content = json_content.strip()
            print(f"提取的JSON内容: {json_content}")
            res_content = json.loads(json_content)
        else:
            # 尝试直接解析
            res_content = json.loads(content_text)
        
        # 添加图像URL到结果中
        if image_url:
            res_content["image_url"] = image_url
            
        return res_content
    except Exception as e:
        logger.error(f"处理API响应时出错: {e}")
        return {
            "error": str(e),
            "is_deleted": True,
            "describe": "图像处理失败",
            "is_related": False,
            "image_url": image_url
        }

# 测试代码
if __name__ == "__main__":
    # 测试图像URL - 使用更可靠的公共图像源
    test_image_url = "https://www.baidu.com/img/PCtm_d9c8750bed0b3c7d089fa7d55720d6cf.png"
    test_theme = "搜索引擎"
    
    # 处理图像
    print("处理图像并获取分析结果...")
    result = process_image(prompt=sample_prompt, image_url=test_image_url, theme=test_theme)
    
    # 打印结果
    if result:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("处理图像失败")
    
def call_gemma3_api(prompt=sample_prompt, image_path: str = None, image_url: str = None, image_content: bytes = None):
    """
    Calls the gemmar3 multimodal API with a prompt and an image.
    The image can be provided in one of three ways:
    1. As a local file path
    2. As a URL to download from
    3. As raw binary content already retrieved

    Args:
        prompt: The text prompt to send to the model.
        image_path: The path to the local image file (optional).
        image_url: The URL of the image to download (optional).
        image_content: Raw binary image content already retrieved (optional).

    Returns:
        Parsed JSON content from the API response or None if an error occurs.
    """
    
    # Check that exactly one image source is provided
    API_URL = "http://localhost:1234/v1/chat/completions"
    sources_provided = sum(x is not None for x in [image_path, image_url, image_content])
    if sources_provided == 0:
        print("Error: One of image_path, image_url, or image_content must be provided")
        return None
    elif sources_provided > 1:
        print("Warning: Multiple image sources provided. Using the first available in order: image_path, image_url, image_content")
    
    # Get image content as base64
    try:
        if image_path is not None:
            # Load from local file
            with open(image_path, 'rb') as f:
                image_base64 = base64.b64encode(f.read()).decode('utf-8')
        elif image_url is not None:
            # Download from URL
            response = requests.get(image_url, stream=True)
            response.raise_for_status()
            image_base64 = base64.b64encode(response.content).decode('utf-8')
        elif image_content is not None:
            # Use already retrieved content
            image_base64 = base64.b64encode(image_content).decode('utf-8')
    except Exception as e:
        print(f"Error processing image: {e}")
        return None

    headers = {
        "Content-Type": "application/json",
        # Add any other necessary headers, like Authorization if required
        # "Authorization": "Bearer YOUR_API_KEY"
    }

    payload = {
        "model": "gemmar3", # Or the specific model name your server expects
        "messages": [
            {
                "role": "system",
                "content": "You are a helpful assistant specialized in image analysis and description. Analyze images thoroughly and provide detailed descriptions. Always respond with valid, properly formatted JSON. Avoid markdown formatting in your responses. If asked to evaluate or classify images, be precise and consistent in your assessments. Focus on visual elements, text content, and contextual information present in the image."   
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
                        "text": prompt.format(theme)
                    }
                ]
            }
        ],
        "max_tokens": 5000  # Optional: Adjust as needed
    }

    try:
        response = requests.post(API_URL, headers=headers, json=payload)
        response.raise_for_status()  # Raise an exception for HTTP errors (4xx or 5xx)
        
        # Get the raw API response
        api_response = response.json()
        
        # Extract the content from the response
        if api_response and 'choices' in api_response and len(api_response['choices']) > 0:
            content = api_response['choices'][0]['message']['content']
            # print(f"Raw API response content: {content}")
            
            # Clean up the content if it's wrapped in markdown code blocks or has extra whitespace
            content = content.strip()
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0].strip()
            elif '```' in content:
                content = content.split('```')[1].split('```')[0].strip()
            
            # Handle potential leading/trailing characters that might break JSON parsing
            # Remove any non-JSON text before the first { and after the last }
            try:
                start_idx = content.index('{')
                end_idx = content.rindex('}') + 1
                content = content[start_idx:end_idx]
            except ValueError:
                print("Could not find valid JSON markers in content")
            
            # Try to parse the JSON content
            try:
                result = json.loads(content)
                # print(f"Successfully parsed JSON: {result}")
                return result
            except json.JSONDecodeError as e:
                print(f"Failed to parse JSON from API response: {e}")
        print("Invalid or incomplete API response structure")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Error calling Gemmar3 API: {e}")
        return None

def process_image(prompt=sample_prompt, image_path: str = None, image_url: str = None, image_content: bytes = None, theme: str = ""):
    if PROCESS_IMAGE_TYPE == "qwen":
        return openai_ali(prompt, image_path, image_url, image_content, theme)
    elif PROCESS_IMAGE_TYPE == "gemma3":
        return call_gemma3_api(prompt, image_path, image_url, image_content, theme)
    else:
        raise ValueError("Invalid PROCESS_IMAGE_TYPE")