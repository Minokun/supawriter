import openai
import pyglet
from settings import LLM_MODEL

def chat(prompt, system_prompt, model_type='deepseek', model_name='deepseek-chat'):
    client = openai.OpenAI(api_key=LLM_MODEL[model_type]['api_key'], base_url=LLM_MODEL[model_type]['base_url'])
    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        max_tokens=2500,
        temperature=0.3,
        stream=False
    )
    return response.choices[0].message.content


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

if __name__ == '__main__':
    prompt = '请叫我如何才能哄女孩子开心'
    system_prompt = "你是一个来自台湾的知心大姐姐，会用最温柔最贴心最绿茶的话和我聊天。"
    response = chat(prompt, system_prompt, model_type='deepseek', model_name='deepseek-v2.5')
    print(response)