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
LLM_MODEL = {
    'deepseek': {
        'model': st.secrets['deepseek']['model'],
        'base_url': st.secrets['deepseek']['base_url'],
        'api_key': st.secrets['deepseek']['api_key']
    },
    'qwen': {
        'model': st.secrets['qwen']['model'],
        'base_url': st.secrets['qwen']['base_url'],
        'api_key': st.secrets['qwen']['api_key']
    },
    'openai': {
        'model': st.secrets['openai']['model'],
        'base_url': st.secrets['openai']['base_url'],
        'api_key': st.secrets['openai']['api_key']
    },
    'yi': {
        'model': st.secrets['yi']['model'],
        'base_url': st.secrets['yi']['base_url'],
        'api_key': st.secrets['yi']['api_key']
    },
    'glm': {
        'model': st.secrets['glm']['model'],
        'base_url': st.secrets['glm']['base_url'],
        'api_key': st.secrets['glm']['api_key']
    },
    'fastgpt': {
        'model': st.secrets['fastgpt']['model'],
        'base_url': st.secrets['fastgpt']['base_url'],
        'api_key': st.secrets['fastgpt']['api_key']
    },
    'xinference': {
        'model': st.secrets['xinference']['model'],
        'base_url': st.secrets['xinference']['base_url'],
        'api_key': st.secrets['xinference']['api_key']
    }
}
