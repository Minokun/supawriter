import openai

api_key = 'sk-Mr1Tt95beGr2ko0u21634797230045639970Aa76B86bB958'
base_url = 'http://192.168.5.31:3000/v1'
client = openai.OpenAI(api_key=api_key, base_url=base_url)


def chat(prompt, system_prompt):
    response = client.chat.completions.create(
        model="qwen1.5-chat",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        max_tokens=20000,
        temperature=0.7
    )
    return response.choices[0].message.content


async def chat_async(prompt, system_prompt):
    response = await client.chat.completions.create(
        model="qwen1.5-chat",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        max_tokens=12000,
        temperature=0.5
    )
    return response.choices[0].message.content


if __name__ == '__main__':
    prompt = "你好"
    system_prompt = "你是一个助手"
    print(chat(prompt, system_prompt))
