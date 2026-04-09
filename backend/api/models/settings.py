# -*- coding: utf-8 -*-
"""设置相关数据模型"""

from pydantic import BaseModel, Field
from typing import Optional

# ============ 模型配置相关 ============

class ModelConfigUpdate(BaseModel):
    """更新模型配置请求"""
    chat_model: Optional[str] = None
    writer_model: Optional[str] = None
    embedding_model: Optional[str] = None
    image_model: Optional[str] = None
    default_temperature: Optional[float] = Field(None, ge=0, le=2)
    default_max_tokens: Optional[int] = Field(None, ge=1, le=128000)
    default_top_p: Optional[float] = Field(None, ge=0, le=1)
    enable_streaming: Optional[bool] = None
    enable_thinking_process: Optional[bool] = None

class ModelConfigResponse(BaseModel):
    """模型配置响应"""
    user_id: int
    chat_model: str
    writer_model: str
    embedding_model: str
    image_model: str
    default_temperature: float
    default_max_tokens: int
    default_top_p: float
    enable_streaming: bool
    enable_thinking_process: bool

# ============ 用户偏好相关 ============

class UserPreferencesUpdate(BaseModel):
    """更新用户偏好请求"""
    editor_font_size: Optional[int] = Field(None, ge=10, le=24)
    editor_theme: Optional[str] = None
    auto_save_interval: Optional[int] = Field(None, ge=10, le=300)
    default_article_style: Optional[str] = None
    default_article_length: Optional[str] = None
    default_language: Optional[str] = None
    sidebar_collapsed: Optional[bool] = None
    theme_mode: Optional[str] = None
    email_notifications: Optional[bool] = None
    task_complete_notification: Optional[bool] = None

class UserPreferencesResponse(BaseModel):
    """用户偏好响应"""
    user_id: int
    editor_font_size: int
    editor_theme: str
    auto_save_interval: int
    default_article_style: str
    default_article_length: str
    default_language: str
    sidebar_collapsed: bool
    theme_mode: str
    email_notifications: bool
    task_complete_notification: bool
