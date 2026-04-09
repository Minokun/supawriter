# -*- coding: utf-8 -*-
"""
AI 助手相关 Pydantic 模型
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class ChatMessage(BaseModel):
    """聊天消息"""
    role: str = Field(..., description="角色: user|assistant|system")
    content: str = Field(..., description="消息内容")
    timestamp: Optional[datetime] = Field(None, description="时间戳")

    # AI 消息特有字段
    is_thinking: Optional[bool] = Field(False, description="是否为思考过程")
    model: Optional[str] = Field(None, description="使用的模型")


class ChatSendRequest(BaseModel):
    """发送消息请求"""
    session_id: Optional[str] = Field(None, description="会话 ID（首次发送为空）")
    message: str = Field(..., min_length=1, description="消息内容")
    model: Optional[str] = Field(None, description="指定模型")
    stream: Optional[bool] = Field(True, description="是否使用流式响应")

    # 网络搜索相关字段
    enable_search: Optional[bool] = Field(False, description="是否启用网络搜索")
    search_results: Optional[int] = Field(5, description="搜索结果数量（默认5条）")
    search_with_content: Optional[bool] = Field(True, description="是否抓取网页内容（默认启用）")


class ChatSession(BaseModel):
    """聊天会话"""
    id: str = Field(..., description="会话 ID")
    user_id: int = Field(..., description="用户 ID")
    title: str = Field(..., description="会话标题")
    messages: List[ChatMessage] = Field(default_factory=list, description="消息列表")
    model: Optional[str] = Field(None, description="默认模型")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    class Config:
        from_attributes = True


class ChatSessionCreate(BaseModel):
    """创建会话请求"""
    title: Optional[str] = Field("新对话", description="会话标题")
    model: Optional[str] = Field(None, description="默认模型")


class ChatSessionUpdate(BaseModel):
    """更新会话请求"""
    title: Optional[str] = Field(None, description="会话标题")
    model: Optional[str] = Field(None, description="默认模型")


class ChatSessionResponse(BaseModel):
    """会话列表响应"""
    items: List[ChatSession] = Field(..., description="会话列表")
    total: int = Field(..., description="总数")


class SearchSource(BaseModel):
    """搜索来源"""
    title: str = Field(..., description="标题")
    url: str = Field(..., description="链接")
    content: str = Field(..., description="摘要或内容")


class SearchContext(BaseModel):
    """搜索上下文信息"""
    query: str = Field(..., description="搜索查询")
    results: List[SearchSource] = Field(default_factory=list, description="搜索结果")
    stats: Optional[Dict[str, Any]] = Field(None, description="搜索统计信息")


class SearchProgressEvent(BaseModel):
    """搜索进度事件"""
    type: str = Field(..., description="事件类型: search_start, search_progress, search_complete")
    stage: Optional[str] = Field(None, description="当前阶段")
    message: Optional[str] = Field(None, description="进度消息")
    progress: Optional[int] = Field(None, description="进度百分比（0-100）")

