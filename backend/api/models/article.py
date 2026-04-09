# -*- coding: utf-8 -*-
"""
文章相关 Pydantic 模型
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class ArticleCreate(BaseModel):
    """创建文章请求"""
    title: str = Field(..., min_length=1, max_length=500, description="文章标题")
    content: Optional[str] = Field(None, description="文章内容（Markdown）")
    tags: Optional[List[str]] = Field(default_factory=list, description="标签列表")
    cover_image: Optional[str] = Field(None, description="封面图片 URL")


class ArticleUpdate(BaseModel):
    """更新文章请求"""
    title: Optional[str] = Field(None, min_length=1, max_length=500, description="文章标题")
    content: Optional[str] = Field(None, description="文章内容（Markdown）")
    tags: Optional[List[str]] = Field(None, description="标签列表")
    cover_image: Optional[str] = Field(None, description="封面图片 URL")


class ArticleResponse(BaseModel):
    """文章响应"""
    id: int = Field(..., description="文章 ID")
    user_id: int = Field(..., description="作者 ID")
    title: str = Field(..., description="文章标题")
    slug: Optional[str] = Field(None, description="URL 友好标识")
    content: Optional[str] = Field(None, description="文章内容")
    html_content: Optional[str] = Field(None, description="渲染后的 HTML")
    cover_image: Optional[str] = Field(None, description="封面图片")
    status: str = Field(..., description="状态: draft|published|archived")

    # SEO 字段
    seo_title: Optional[str] = Field(None, description="SEO 标题")
    seo_desc: Optional[str] = Field(None, description="SEO 描述")
    seo_keywords: Optional[str] = Field(None, description="SEO 关键词")

    # 统计数据
    view_count: int = Field(default=0, description="浏览数")
    like_count: int = Field(default=0, description="点赞数")
    comment_count: int = Field(default=0, description="评论数")
    favorite_count: int = Field(default=0, description="收藏数")

    # 时间戳
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    published_at: Optional[datetime] = Field(None, description="发布时间")

    # 标签和元数据
    tags: List[str] = Field(default_factory=list, description="标签列表")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")

    class Config:
        from_attributes = True


class ArticleListResponse(BaseModel):
    """文章列表响应"""
    items: List[ArticleResponse] = Field(..., description="文章列表")
    total: int = Field(..., description="总数")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页数量")
    total_pages: int = Field(..., description="总页数")


class ArticleGenerateRequest(BaseModel):
    """AI 生成文章请求"""
    topic: str = Field(..., min_length=1, description="文章主题")
    article_type: Optional[str] = Field(default="blog", description="文章类型")
    custom_style: Optional[str] = Field(None, description="自定义风格要求")
    spider_num: Optional[int] = Field(default=10, description="爬取参考文章数量")
    enable_images: Optional[bool] = Field(default=True, description="是否生成图片")
    extra_urls: Optional[List[str]] = Field(default_factory=list, description="额外参考URL")
    model_type: Optional[str] = Field(default="deepseek", description="LLM提供商")
    model_name: Optional[str] = Field(default="deepseek-chat", description="LLM模型名称")


class ArticlePublishRequest(BaseModel):
    """发布文章请求"""
    seo_title: Optional[str] = Field(None, description="SEO 标题")
    seo_desc: Optional[str] = Field(None, description="SEO 描述")
    seo_keywords: Optional[str] = Field(None, description="SEO 关键词")
    tags: Optional[List[str]] = Field(None, description="标签列表")
    cover_image: Optional[str] = Field(None, description="封面图片")


class TaskProgress(BaseModel):
    """任务进度"""
    task_id: str = Field(..., description="任务 ID")
    user_id: Optional[int] = Field(None, description="用户 ID")
    topic: Optional[str] = Field(None, description="文章主题")
    status: str = Field(..., description="状态: queued|running|completed|error")
    progress: int = Field(default=0, ge=0, le=100, description="进度百分比")
    progress_text: Optional[str] = Field(None, description="进度描述")
    live_article: Optional[str] = Field(None, description="实时生成的文章")
    outline: Optional[Dict[str, Any]] = Field(None, description="文章大纲")
    error: Optional[str] = Field(None, description="错误信息")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    article_type: Optional[str] = Field(None, description="文章类型")


class QueueResponse(BaseModel):
    """队列响应"""
    items: List[TaskProgress] = Field(..., description="任务列表")
    total: int = Field(..., description="总数")
