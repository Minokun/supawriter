import openai
import pyglet
import time
import json
from settings import LLM_MODEL

def chat(prompt, system_prompt, model_type='deepseek', model_name='deepseek-chat', max_retries=3):
    """
    与LLM模型进行对话
    :param prompt: 用户提示词
    :param system_prompt: 系统提示词
    :param model_type: 模型类型
    :param model_name: 模型名称
    :param max_retries: 最大重试次数
    :return: 模型回复内容
    """
    retries = 0
    last_error = None
    
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
            
            # 发送请求
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                stream=False
            )
            
            # 返回结果
            return response.choices[0].message.content
            
        except openai.APIError as e:
            last_error = e
            print(f"API错误 (尝试 {retries+1}/{max_retries}): {str(e)}")
        except openai.APIConnectionError as e:
            last_error = e
            print(f"API连接错误 (尝试 {retries+1}/{max_retries}): {str(e)}")
        except openai.RateLimitError as e:
            last_error = e
            print(f"API速率限制错误 (尝试 {retries+1}/{max_retries}): {str(e)}")
            # 速率限制错误可能需要更长的等待时间
            time.sleep(2 * (retries + 1))
        except json.JSONDecodeError as e:
            last_error = e
            print(f"JSON解析错误 (尝试 {retries+1}/{max_retries}): {str(e)}")
        except Exception as e:
            last_error = e
            print(f"未知错误 (尝试 {retries+1}/{max_retries}): {str(e)}")
        
        # 增加重试次数并等待
        retries += 1
        if retries < max_retries:
            # 指数退避策略
            time.sleep(1 * retries)
    
    # 所有重试都失败了，抛出异常
    error_message = f"LLM模型连接失败: {str(last_error)}"
    print(error_message)
    raise ConnectionError(error_message)


async def chat_async(prompt, system_prompt):
    client = openai.OpenAI(api_key=LLM_MODEL['qwen'].api_key, base_url=LLM_MODEL['qwen'].base_url)
    model = 'qwen-1.5'
    response = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        max_tokens=12000,
        temperature=0.5
    )
    return response.choices[0].message.content

def text_2_speech(input_text, mp3_file_name='speech.mp3'):
    client = openai.OpenAI(api_key=LLM_MODEL['qwen'].api_key, base_url=LLM_MODEL['qwen'].base_url)
    model_name = "ChatTTS"
    response = client.audio.speech.create(
        model=model_name,
        voice=359154910,
        input=input_text
    )
    response.stream_to_file(mp3_file_name)

def on_player_eos():
    """当播放结束时调用的回调函数，用于退出应用"""
    pyglet.app.exit()

def multimodal_response(img):
    client = openai.OpenAI(api_key=LLM_MODEL['qwen'].api_key, base_url=LLM_MODEL['qwen'].base_url)
    model = 'qwen-1.5'
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "你是一个来自台湾的知心大姐姐，会用最温柔最贴心最绿茶的话和我聊天。"},
            {"role": "user", "content":"请帮我用最温柔的话，用最compact的话，用最compact"}
        ]
    )
    return response

if __name__ == '__main__':
    prompt = '请叫我如何才能哄女孩子开心'
    system_prompt = "你是一个来自台湾的知心大姐姐，会用最温柔最贴心最绿茶的话和我聊天。"
    response = chat(prompt, system_prompt, model_type='xinference', model_name='qwen2.5-instruct')
    print(response)