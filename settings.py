# -*- coding: utf-8 -*-
# 将当前目录目录设置到环境变量中
import os
import sys
import streamlit as st
from openai import OpenAI

base_path = os.path.dirname(os.path.abspath(__file__))
sys.path.append(base_path)

WEB_SERVER_PORT = 90

# OpenAI client initialization
# Default to the first provider in LLM_PROVIDERS
default_provider = 'openai'  # Will be overridden if available in LLM_PROVIDERS
openai_model = None  # Will be set after LLM_MODEL is defined

# List of supported LLM models - model names are fetched from secrets
# LLM_PROVIDERS = ['deepseek', 'qwen', 'openai', 'yi', 'glm', 'fastgpt', 'xinference']

LLM_PROVIDERS = [
    key for key in st.secrets.keys()
    if hasattr(st.secrets[key], 'keys')
]

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

# Initialize OpenAI client with default provider (first available)
default_provider = LLM_PROVIDERS[0] if LLM_PROVIDERS else 'openai'
client = OpenAI(
    api_key=LLM_MODEL[default_provider]['api_key'],
    base_url=LLM_MODEL[default_provider]['base_url']
)
openai_model = LLM_MODEL[default_provider]['model'][0] if isinstance(LLM_MODEL[default_provider]['model'], list) else LLM_MODEL[default_provider]['model']

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

# Embedding settings
# 导入配置管理器，如果导入失败则使用默认值
try:
    from utils.config_manager import get_embedding_type, get_embedding_model, get_embedding_dimension, get_embedding_timeout
    EMBEDDING_TYPE = get_embedding_type()  # Options: gitee, xinference, jina, local
    EMBEDDING_D = get_embedding_dimension()
    EMBEDDING_MODEL = get_embedding_model()
    EMBEDDING_TIMEOUT = get_embedding_timeout()
except ImportError:
    # 如果配置管理器未导入成功，使用默认值
    EMBEDDING_TYPE = 'xinference'
    EMBEDDING_D = 2048
    EMBEDDING_MODEL = 'jina-embeddings-v4'
    EMBEDDING_TIMEOUT = 10
EMBEDDING_CONFIG = {
    'gitee': {
        'model': EMBEDDING_MODEL,
        'host': st.secrets['gitee']['base_url'],
        'api_key': st.secrets['gitee']['api_key'],
        'timeout': EMBEDDING_TIMEOUT
    },
    'xinference': {
        'model': EMBEDDING_MODEL,
        'host': st.secrets['xinference']['base_url'] + '/embeddings',
        'api_key': st.secrets['xinference']['api_key'],
        'timeout': EMBEDDING_TIMEOUT
    },
    'jina': {
        'model': EMBEDDING_MODEL,
        'host': st.secrets['jina']['base_url'] + '/embeddings',
        'api_key': st.secrets['jina']['api_key'],
        'timeout': EMBEDDING_TIMEOUT
    }
}

# 网页显示设置
HTML_NGINX_BASE_URL = 'http://localhost:80/'

# openai vl设置
PROCESS_IMAGE_TYPE = "glm" # 使用qwen glm模型
# 免费模型还有 qwen-vl-max-2025-04-08 qwen-vl-max-2025-04-02 qwen-vl-max-2025-01-25 qwen-vl-plus-2025-01-25
PROCESS_CONFIG = {
    "qwen": {
        "model": "qwen-vl-plus-2025-01-25",
        "api_key": st.secrets['dashscope']['api_key'],
        "base_url": st.secrets['dashscope']['base_url']
    },
    "glm": {
        "model": "glm-4.1v-thinking-flash",
        "api_key": st.secrets['glm']['api_key'],
        "base_url": st.secrets['glm']['base_url']
    }
}

# 文章生成设置
# 爬取网页数量默认值
DEFAULT_SPIDER_NUM = 2
# 是否自动插入相关图片默认值
DEFAULT_ENABLE_IMAGES = True
# 是否将图片下载至本地默认值
DEFAULT_DOWNLOAD_IMAGES = True