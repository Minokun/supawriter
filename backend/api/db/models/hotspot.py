# -*- coding: utf-8 -*-
"""Hotspot ORM models for newsnow integration.

热点数据模型 - 支持多平台热点数据持久化和排名变化追踪
"""

from sqlalchemy import String, Text, Boolean, Integer, DateTime, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional, List
from datetime import datetime, timezone

from backend.api.db.base import Base


class HotspotSource(Base):
    """平台配置表 - 存储支持的热点平台信息"""
    __tablename__ = 'hotspot_sources'

    id: Mapped[str] = mapped_column(String(50), primary_key=True)  # baidu, weibo, douyin...
    name: Mapped[str] = mapped_column(String(100), nullable=False)  # 百度热搜, 微博热搜...
    icon: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)  # emoji icon
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # 综合, 短视频, 财经...

    # Relationships
    items: Mapped[List["HotspotItem"]] = relationship(
        "HotspotItem",
        back_populates="source_info",
        cascade="all, delete-orphan"
    )


class HotspotItem(Base):
    """热点主表 - 存储热点条目及其当前状态"""
    __tablename__ = 'hotspot_items'
    __table_args__ = (
        UniqueConstraint('title', 'source', name='uq_hotspot_title_source'),
        Index('ix_hotspot_items_source_rank', 'source', 'rank'),
        Index('ix_hotspot_items_title', 'title'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)  # 原链接
    source: Mapped[str] = mapped_column(String(50), ForeignKey('hotspot_sources.id'), nullable=False, index=True)
    source_id: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)  # 平台内部 ID

    # 排名相关
    rank: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rank_prev: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 上次排名
    rank_change: Mapped[int] = mapped_column(Integer, nullable=False, default=0)  # 排名变化 (正升负降)

    # 热度相关
    hot_value: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 热度值
    hot_value_prev: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 上次热度值

    # 状态
    is_new: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # 是否新增热点
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # 描述/摘要
    icon_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)  # 热榜标记图标
    mobile_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)  # 移动端链接

    # 时间戳
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    source_info: Mapped["HotspotSource"] = relationship("HotspotSource", back_populates="items")
    rank_history: Mapped[List["HotspotRankHistory"]] = relationship(
        "HotspotRankHistory",
        back_populates="hotspot_item",
        cascade="all, delete-orphan"
    )


class HotspotRankHistory(Base):
    """排名历史表 - 记录热点排名和热度的历史变化"""
    __tablename__ = 'hotspot_rank_history'
    __table_args__ = (
        Index('ix_rank_history_item_time', 'hotspot_item_id', 'recorded_at'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    hotspot_item_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey('hotspot_items.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    source: Mapped[str] = mapped_column(String(50), nullable=False)  # 冗余存储，便于查询

    # 记录时的排名和热度
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    hot_value: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_new: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # 记录时间
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )

    # Relationships
    hotspot_item: Mapped["HotspotItem"] = relationship("HotspotItem", back_populates="rank_history")