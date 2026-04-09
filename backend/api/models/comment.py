# -*- coding: utf-8 -*-
"""
评论相关 Pydantic 模型
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class CommentCreate(BaseModel):
    """创建评论请求"""
    article_id: int = Field(..., description="文章 ID")
    content: str = Field(..., min_length=1, max_length=5000, description="评论内容")
    parent_id: Optional[int] = Field(None, description="父评论 ID（回复时使用）")


class CommentUpdate(BaseModel):
    """更新评论请求"""
    content: str = Field(..., min_length=1, max_length=5000, description="评论内容")


class CommentResponse(BaseModel):
    """评论响应"""
    id: int = Field(..., description="评论 ID")
    article_id: int = Field(..., description="文章 ID")
    user_id: int = Field(..., description="评论者 ID")
    content: str = Field(..., description="评论内容")
    parent_id: Optional[int] = Field(None, description="父评论 ID")

    # 用户信息（内嵌）
    user_name: Optional[str] = Field(None, description="评论者名称")
    user_avatar: Optional[str] = Field(None, description="评论者头像")

    # 统计
    like_count: int = Field(default=0, description="点赞数")

    # 时间戳
    created_at: datetime = Field(..., description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")

    # 子评论（内嵌）
    replies: Optional[List["CommentResponse"]] = Field(default_factory=list, description="回复列表")

    class Config:
        from_attributes = True


class CommentListResponse(BaseModel):
    """评论列表响应"""
    items: List[CommentResponse] = Field(..., description="评论列表")
    total: int = Field(..., description="总数")
