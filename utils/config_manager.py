#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import logging
import time
from pathlib import Path
import streamlit as st

logger = logging.getLogger(__name__)

class ConfigManager:
    """
    管理系统配置的类，提供持久化存储和读取功能
    """
    
    def __init__(self, config_dir='data/config'):
        """
        初始化配置管理器
        
        Args:
            config_dir: 配置文件存储目录
        """
        self.config_dir = config_dir
        self.ensure_config_dir()
        # 添加内存缓存
        self._config_cache = {}  # 格式: {username: {'data': config_dict, 'mtime': timestamp}}
        
    def ensure_config_dir(self):
        """确保配置目录存在"""
        Path(self.config_dir).mkdir(parents=True, exist_ok=True)
        
    def get_user_config_path(self, username):
        """
        获取用户配置文件路径
        
        Args:
            username: 用户名
            
        Returns:
            str: 用户配置文件的完整路径
        """
        if not username:
            username = 'default'
        return os.path.join(self.config_dir, f"{username}_config.json")
        
    def save_config(self, config_data, username=None):
        """
        保存用户配置
        
        Args:
            config_data: 要保存的配置数据字典
            username: 用户名，如果为None则使用默认用户
            
        Returns:
            bool: 保存是否成功
        """
        try:
            config_path = self.get_user_config_path(username)
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, ensure_ascii=False, indent=2)
            
            # 更新缓存
            if not username:
                username = 'default'
            self._config_cache[username] = {
                'data': config_data.copy(),
                'mtime': os.path.getmtime(config_path)
            }
            
            logger.info(f"配置已保存到 {config_path}")
            return True
        except Exception as e:
            logger.error(f"保存配置失败: {str(e)}")
            return False
            
    def load_config(self, username=None):
        """
        加载用户配置
        
        Args:
            username: 用户名，如果为None则使用默认用户
            
        Returns:
            dict: 配置数据字典，如果加载失败则返回空字典
        """
        if not username:
            username = 'default'
            
        config_path = self.get_user_config_path(username)
        
        try:
            # 检查文件是否存在
            if not os.path.exists(config_path):
                # 文件不存在，返回空配置
                if username not in self._config_cache:
                    logger.info(f"配置文件 {config_path} 不存在，将使用默认配置")
                    self._config_cache[username] = {'data': {}, 'mtime': 0}
                return self._config_cache[username]['data'].copy()
            
            # 获取文件修改时间
            current_mtime = os.path.getmtime(config_path)
            
            # 检查缓存是否存在且是否为最新
            if (username in self._config_cache and 
                self._config_cache[username]['mtime'] >= current_mtime):
                # 使用缓存数据
                return self._config_cache[username]['data'].copy()
            
            # 缓存不存在或已过期，从文件加载
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            # 更新缓存
            self._config_cache[username] = {
                'data': config_data.copy(),
                'mtime': current_mtime
            }
            
            logger.info(f"已从 {config_path} 加载配置")
            return config_data
        except Exception as e:
            logger.error(f"加载配置失败: {str(e)}")
            # 如果加载失败但缓存存在，使用缓存
            if username in self._config_cache:
                return self._config_cache[username]['data'].copy()
            # 否则返回空字典
            return {}
            
    def get_config_value(self, key, default_value=None, username=None):
        """
        获取配置值
        
        Args:
            key: 配置键
            default_value: 默认值，如果配置不存在则返回此值
            username: 用户名，如果为None则使用默认用户
            
        Returns:
            任意类型: 配置值或默认值
        """
        config = self.load_config(username)
        return config.get(key, default_value)
        
    def set_config_value(self, key, value, username=None):
        """
        设置配置值
        
        Args:
            key: 配置键
            value: 配置值
            username: 用户名，如果为None则使用默认用户
            
        Returns:
            bool: 设置是否成功
        """
        config = self.load_config(username)
        config[key] = value
        return self.save_config(config, username)
        
    def delete_config_value(self, key, username=None):
        """
        删除配置值
        
        Args:
            key: 配置键
            username: 用户名，如果为None则使用默认用户
            
        Returns:
            bool: 删除是否成功
        """
        config = self.load_config(username)
        if key in config:
            del config[key]
            return self.save_config(config, username)
        return True  # 键不存在也视为成功
        
    def clear_cache(self, username=None):
        """
        清除配置缓存
        
        Args:
            username: 用户名，如果为None则清除所有缓存
            
        Returns:
            None
        """
        if username:
            if username in self._config_cache:
                del self._config_cache[username]
        else:
            self._config_cache.clear()

# 创建全局配置管理器实例
config_manager = ConfigManager()

# 默认配置值
DEFAULT_CONFIG = {
    'global_model_settings': {
        'provider': 'openai',  # 默认提供商
        'model_name': 'gpt-3.5-turbo'  # 默认模型
    },
    'embedding_settings': {
        'type': 'xinference',  # 默认嵌入类型: gitee, xinference, jina, local
        'model': 'jina-embeddings-v4',  # 默认嵌入模型
        'dimension': 2048,  # 默认嵌入维度
        'timeout': 10  # 默认超时时间
    }
}

def get_current_user():
    """
    获取当前登录用户
    
    Returns:
        str: 当前用户名，如果未登录则返回None
    """
    if 'username' in st.session_state:
        return st.session_state.username
    return None

def get_config(key=None, default_value=None):
    """
    获取配置值的便捷函数
    
    Args:
        key: 配置键，如果为None则返回整个配置
        default_value: 默认值
        
    Returns:
        任意类型: 配置值或整个配置字典
    """
    username = get_current_user()
    
    if key is None:
        # 返回整个配置
        user_config = config_manager.load_config(username)
        # 合并默认配置
        for default_key, default_val in DEFAULT_CONFIG.items():
            if default_key not in user_config:
                user_config[default_key] = default_val
        return user_config
    else:
        # 返回特定配置值
        value = config_manager.get_config_value(key, None, username)
        if value is None and key in DEFAULT_CONFIG:
            return DEFAULT_CONFIG[key]
        elif value is None:
            return default_value
        return value

def set_config(key, value):
    """
    设置配置值的便捷函数
    
    Args:
        key: 配置键
        value: 配置值
        
    Returns:
        bool: 设置是否成功
    """
    username = get_current_user()
    return config_manager.set_config_value(key, value, username)

def get_embedding_type():
    """
    获取当前嵌入类型
    
    Returns:
        str: 嵌入类型
    """
    embedding_settings = get_config('embedding_settings')
    return embedding_settings.get('type', 'xinference')

def get_embedding_model():
    """
    获取当前嵌入模型
    
    Returns:
        str: 嵌入模型
    """
    embedding_settings = get_config('embedding_settings')
    return embedding_settings.get('model', 'jina-embeddings-v4')

def get_embedding_dimension():
    """
    获取当前嵌入维度
    
    Returns:
        int: 嵌入维度
    """
    embedding_settings = get_config('embedding_settings')
    return embedding_settings.get('dimension', 2048)

def get_embedding_timeout():
    """
    获取当前嵌入超时时间
    
    Returns:
        int: 超时时间（秒）
    """
    embedding_settings = get_config('embedding_settings')
    return embedding_settings.get('timeout', 10)
