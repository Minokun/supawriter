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
LLM_PROVIDERS = ['deepseek', 'hs-deepseek', 'qwen', 'openai', 'yi', 'glm', 'fastgpt', 'xinference']

LLM_MODEL: dict[str, dict[str, str]] = {
    # ... (existing content)
}

# Import prompt templates for transformations
import utils.prompt_template as pt

# The following is the original content
LLM_MODEL: dict[str, dict[str, str]] = {
    provider: {
        'model': st.secrets[provider]['model'],
        'base_url': st.secrets[provider]['base_url'],
        'api_key': st.secrets[provider]['api_key']
    }
    for provider in LLM_PROVIDERS
}

# Article Transformation Options
# Maps display name to prompt template
ARTICLE_TRANSFORMATIONS = {
    "转换为白话文": pt.CONVERT_2_SIMPLE,
    "转换为Bento风格网页": pt.BENTO_WEB_PAGE,
    # Add more transformations here in the future, e.g.:
    # "总结为要点": pt.SUMMARIZE_KEY_POINTS, 
    # "扩写段落": pt.EXPAND_PARAGRAPH,
}

# History Filter Options
# Base options, transformation types will be added dynamically
HISTORY_FILTER_BASE_OPTIONS = [
    "所有文章", 
    "完成文章" # Represents original, non-transformed articles
]

# Embedding settings 三种选项 gitee, xinference, local
EMBEDDING_TYPE = 'gitee'
# 模力方舟embedding设置
EMBEDDING_MODEL_gitee = 'Qwen3-Embedding-8B'
EMBEDDING_HOST_gitee = 'https://ai.gitee.com/v1'
EMBEDDING_API_KEY_gitee = 'U2PS8VI0XDMTMRAHB5XVMDGOTTD7H4KKSM6EQRN9'
EMBEDDING_TIMEOUT_gitee = 5
# xinference embedding设置
EMBEDDING_MODEL_xinference = 'Qwen3-Embedding-8B'
EMBEDDING_HOST_xinference = 'http://localhost:9997/v1'
EMBEDDING_TIMEOUT_xinference = 5

# 网页显示设置
HTML_NGINX_BASE_URL = 'http://localhost:80/'