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
EMBEDDING_TYPE = 'gitee' # Options: gitee, xinference, jina, local

EMBEDDING_CONFIG = {
    'gitee': {
        'model': 'jina-embeddings-v4',
        'host': 'https://ai.gitee.com/v1',
        'api_key': 'U2PS8VI0XDMTMRAHB5XVMDGOTTD7H4KKSM6EQRN9',
        'timeout': 10
    },
    'xinference': {
        'model': 'Qwen3-Embedding-8B',
        'host': 'http://localhost:9997/v1',
        'api_key': 'not-needed', # xinference usually doesn't require an API key
        'timeout': 10
    },
    'jina': {
        'model': 'jina-embeddings-v4',
        'host': 'https://api.jina.ai/v1',
        'api_key': 'jina_78bd66d1a7194ff8bf7942ae59779dac-ScGeQdHO_3OmFzHcLClLC_DFE0R',
        'timeout': 10
    },
    'local': {
        'model': 'BAAI/bge-large-zh-v1.5',
        # For local models, host, api_key, and timeout are not applicable
    }
}

# 网页显示设置
HTML_NGINX_BASE_URL = 'http://localhost:80/'

# openai vl设置
PROCESS_IMAGE_TYPE = "qwen" # 2种选项 gemma3, qwen
OPENAI_VL_MODEL = 'qwen-vl-plus-2025-05-07'
OPENAI_VL_API_KEY = 'sk-cabc155d7d094825b2b1f0e9ffea35dd'
OPENAI_VL_BASE_URL = 'https://dashscope.aliyuncs.com/compatible-mode/v1'

# 文章生成设置
# 爬取网页数量默认值
DEFAULT_SPIDER_NUM = 30
# 是否自动插入相关图片默认值
DEFAULT_ENABLE_IMAGES = True
# 是否将图片下载至本地默认值
DEFAULT_DOWNLOAD_IMAGES = True