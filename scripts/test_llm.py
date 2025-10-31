from openai import OpenAI
import streamlit as st

base_url = st.secrets['minimax'].base_url
api_key = st.secrets['minimax'].api_key
model_name = st.secrets['minimax'].model[0]
print(base_url, api_key, model_name)
client = OpenAI(
    base_url=base_url,
    api_key=api_key
)

stream = client.chat.completions.create(
    model=model_name,
    messages=[
        {
            "role": "user",
            "content": "写一首关于春天的诗"
        }
    ],
    stream=True
)

for chunk in stream:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="", flush=True)