# -*- coding: utf-8 -*-
# 将当前目录目录设置到环境变量中
import os
import sys
import streamlit as st

base_path = os.path.dirname(os.path.abspath(__file__))
sys.path.append(base_path)

WEB_SERVER_PORT = 90

# llm settings
MODEL_LIST = st.secrets['model_list']

# List of supported LLM models
LLM_PROVIDERS = ['hs-deepseek', 'deepseek', 'qwen', 'openai', 'yi', 'glm', 'fastgpt', 'xinference']

LLM_MODEL: dict[str, dict[str, str]] = {
    provider: {
        'model': st.secrets[provider]['model'],
        'base_url': st.secrets[provider]['base_url'],
        'api_key': st.secrets[provider]['api_key']
    }
    for provider in LLM_PROVIDERS
}
