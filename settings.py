# -*- coding: utf-8 -*-
# 将当前目录目录设置到环境变量中
import os
import sys

base_path = os.path.dirname(os.path.abspath(__file__))
sys.path.append(base_path)

WEB_SERVER_PORT = 90

# llm settings
MODEL_LIST = ["qwen1.5-chat", 'gpt-4o', 'yi-large-turbo', 'yi-medium-200k', 'deepseek-chat', 'deepseek-coder', 'glm-4-air', 'glm-4-plus', 'glm-4-flash']
LLM_MODEL = {
    'deepseek': {
        'model': ['deepseek-chat', 'deepseek-coder', 'deepseek-v2.5'],
        'base_url': 'https://api.deepseek.com',
        'api_key': 'sk-d4ed7eac162b45819a9d2b8e5f6fe7c8'
    },
    'qwen': {
        'model': ['qwen1.5-chat'],
        'base_url': 'http://192.168.16.13:3000/v1',
        'api_key': 'sk-Mr1Tt95beGr2ko0u21634797230045639970Aa76B86bB958'
    },
    'chatgpt': {
        'model': ['gpt-4o'],
        'base_url': '',
        'api_key': ''
    },
    'yi': {
        'model': ['yi-large-turbo', 'yi-medium-200k'],
        'base_url': 'https://api.lingyiwanwu.com/v1',
        'api_key': 'c2ae7f8b1d3f4b5e8c95dbfa0952bbf7'
    },
    'glm': {
        'model': ['glm-4-air', 'glm-4-plus', 'glm-4-flash'],
        'base_url': 'https://open.bigmodel.cn/api/paas/v4/',
        'api_key': 'fc83879fbfd804b3d7e451f7ac37cf73.MfgrE5stsBGoXrJY'
    },
    'fastgpt': {
        'model': ['qwen-1.5'],
        'base_url': 'http://192.168.16.13/api/v1',
        'api_key': 'fastgpt-Ryz6CGWUJe5S3T3NKp4La8gWFmXrRWXfet4fuZFqz1BxvMGEwPanDz'
    }
}
