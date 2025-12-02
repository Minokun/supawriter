# -*- coding: utf-8 -*-
"""
文章撰写队列管理模块

提供文章任务的队列管理功能，支持：
- 添加任务到队列
- 从队列中移除任务
- 调整任务顺序
- 获取下一个待执行任务
- 持久化队列状态

注意：使用全局变量存储队列，以便后台线程也能访问
"""

import streamlit as st
import json
import os
import uuid
from datetime import datetime
from typing import Optional, Dict, List, Any
import logging
import threading

logger = logging.getLogger(__name__)

# 队列状态常量
QUEUE_STATUS_PENDING = 'pending'      # 等待执行
QUEUE_STATUS_RUNNING = 'running'      # 正在执行
QUEUE_STATUS_COMPLETED = 'completed'  # 已完成
QUEUE_STATUS_ERROR = 'error'          # 执行失败

# 任务来源常量
SOURCE_MANUAL = 'manual'              # 手动填写
SOURCE_TWEET_TOPICS = 'tweet_topics'  # 推文主题
SOURCE_HOTSPOTS = 'hotspots'          # 全网热点
SOURCE_NEWS = 'news'                  # 新闻资讯

# 全局队列存储（线程安全）
_global_queue: List[Dict[str, Any]] = []
_queue_lock = threading.Lock()


def _get_queue_key() -> str:
    """获取当前用户的队列 session key"""
    return 'article_queue'


def _get_queue() -> List[Dict[str, Any]]:
    """获取当前队列（使用全局变量，线程安全）"""
    global _global_queue
    with _queue_lock:
        return _global_queue


def _save_queue(queue: List[Dict[str, Any]]):
    """保存队列（使用全局变量，线程安全）"""
    global _global_queue
    with _queue_lock:
        _global_queue = queue


def create_task(
    topic: str,
    source: str = SOURCE_MANUAL,
    custom_style: str = '',
    extra_urls: List[str] = None,
    metadata: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    创建一个新的文章任务
    
    Args:
        topic: 文章主题
        source: 任务来源
        custom_style: 自定义写作风格
        extra_urls: 额外的URL列表
        metadata: 额外的元数据（如热点来源、推文角度等）
    
    Returns:
        任务字典
    """
    task_id = str(uuid.uuid4())[:8]
    now = datetime.now()
    
    task = {
        'id': task_id,
        'topic': topic,
        'source': source,
        'custom_style': custom_style or '',
        'extra_urls': extra_urls or [],
        'metadata': metadata or {},
        'status': QUEUE_STATUS_PENDING,
        'created_at': now.isoformat(),
        'started_at': None,
        'completed_at': None,
        'error_message': None,
        'priority': 0,  # 数字越小优先级越高
    }
    
    return task


def check_duplicate_topic(topic: str) -> Optional[Dict[str, Any]]:
    """
    检查队列中是否已存在相同主题的任务（pending 或 running 状态）
    
    Args:
        topic: 文章主题
    
    Returns:
        如果存在重复，返回已存在的任务；否则返回 None
    """
    queue = _get_queue()
    topic_normalized = topic.strip().lower()
    
    for task in queue:
        if task['status'] in [QUEUE_STATUS_PENDING, QUEUE_STATUS_RUNNING]:
            existing_topic = task['topic'].strip().lower()
            # 完全匹配或高度相似（一个包含另一个且长度差不超过10）
            if existing_topic == topic_normalized:
                return task
            # 检查是否一个是另一个的子串（防止略微修改后重复提交）
            if len(topic_normalized) > 10 and len(existing_topic) > 10:
                if topic_normalized in existing_topic or existing_topic in topic_normalized:
                    if abs(len(topic_normalized) - len(existing_topic)) <= 10:
                        return task
    return None


def add_to_queue(
    topic: str,
    source: str = SOURCE_MANUAL,
    custom_style: str = "",
    extra_urls: list = None,
    priority: int = 0,
    metadata: dict = None,
    insert_first: bool = False,
    allow_duplicate: bool = False
) -> Optional[dict]:
    """
    添加任务到队列
    
    Args:
        topic: 文章主题
        source: 任务来源
        custom_style: 自定义写作风格
        extra_urls: 额外的URL列表
        metadata: 额外的元数据
        priority: 优先级（数字越小优先级越高）
        insert_first: 是否插入到队列最前面（优先执行）
        allow_duplicate: 是否允许重复主题（默认不允许）
    
    Returns:
        添加的任务，如果是重复任务且不允许重复则返回 None
    """
    # 检查重复
    if not allow_duplicate:
        duplicate = check_duplicate_topic(topic)
        if duplicate:
            logger.warning(f"检测到重复主题，已跳过: {topic[:30]}... (已存在任务: {duplicate['id']})")
            return None
    
    queue = _get_queue()
    task = create_task(topic, source, custom_style, extra_urls, metadata)
    
    if priority is not None:
        task['priority'] = priority
    
    if insert_first:
        # 插入到第一个 pending 任务之前
        insert_pos = 0
        for i, existing_task in enumerate(queue):
            if existing_task['status'] == QUEUE_STATUS_PENDING:
                insert_pos = i
                break
            insert_pos = i + 1
        queue.insert(insert_pos, task)
    elif priority is not None:
        # 按优先级插入
        inserted = False
        for i, existing_task in enumerate(queue):
            if existing_task['status'] == QUEUE_STATUS_PENDING and existing_task.get('priority', 0) > priority:
                queue.insert(i, task)
                inserted = True
                break
        if not inserted:
            queue.append(task)
    else:
        queue.append(task)
    
    _save_queue(queue)
    logger.info(f"任务已添加到队列: {task['id']} - {topic[:30]}...")
    return task


def remove_from_queue(task_id: str) -> bool:
    """
    从队列中移除任务
    
    Args:
        task_id: 任务ID
    
    Returns:
        是否成功移除
    """
    queue = _get_queue()
    for i, task in enumerate(queue):
        if task['id'] == task_id:
            # 只能移除待执行的任务
            if task['status'] == QUEUE_STATUS_PENDING:
                queue.pop(i)
                _save_queue(queue)
                logger.info(f"任务已从队列移除: {task_id}")
                return True
            else:
                logger.warning(f"无法移除非待执行状态的任务: {task_id}, status={task['status']}")
                return False
    return False


def move_task(task_id: str, direction: str) -> bool:
    """
    移动任务位置
    
    Args:
        task_id: 任务ID
        direction: 'up' 或 'down'
    
    Returns:
        是否成功移动
    """
    queue = _get_queue()
    pending_tasks = [(i, t) for i, t in enumerate(queue) if t['status'] == QUEUE_STATUS_PENDING]
    
    for idx, (queue_idx, task) in enumerate(pending_tasks):
        if task['id'] == task_id:
            if direction == 'up' and idx > 0:
                # 与上一个待执行任务交换
                prev_queue_idx = pending_tasks[idx - 1][0]
                queue[queue_idx], queue[prev_queue_idx] = queue[prev_queue_idx], queue[queue_idx]
                _save_queue(queue)
                return True
            elif direction == 'down' and idx < len(pending_tasks) - 1:
                # 与下一个待执行任务交换
                next_queue_idx = pending_tasks[idx + 1][0]
                queue[queue_idx], queue[next_queue_idx] = queue[next_queue_idx], queue[queue_idx]
                _save_queue(queue)
                return True
    return False


def get_next_pending_task() -> Optional[Dict[str, Any]]:
    """
    获取下一个待执行的任务
    
    Returns:
        待执行的任务，如果没有则返回 None
    """
    queue = _get_queue()
    for task in queue:
        if task['status'] == QUEUE_STATUS_PENDING:
            return task
    return None


def get_running_task() -> Optional[Dict[str, Any]]:
    """
    获取当前正在执行的任务
    
    Returns:
        正在执行的任务，如果没有则返回 None
    """
    queue = _get_queue()
    for task in queue:
        if task['status'] == QUEUE_STATUS_RUNNING:
            return task
    return None


def start_task(task_id: str) -> bool:
    """
    标记任务开始执行
    
    Args:
        task_id: 任务ID
    
    Returns:
        是否成功
    """
    queue = _get_queue()
    for task in queue:
        if task['id'] == task_id:
            task['status'] = QUEUE_STATUS_RUNNING
            task['started_at'] = datetime.now().isoformat()
            _save_queue(queue)
            logger.info(f"任务开始执行: {task_id}")
            return True
    return False


def complete_task(task_id: str, success: bool = True, error_message: str = None) -> bool:
    """
    标记任务完成
    
    Args:
        task_id: 任务ID
        success: 是否成功
        error_message: 错误信息（如果失败）
    
    Returns:
        是否成功
    """
    queue = _get_queue()
    for task in queue:
        if task['id'] == task_id:
            task['status'] = QUEUE_STATUS_COMPLETED if success else QUEUE_STATUS_ERROR
            task['completed_at'] = datetime.now().isoformat()
            if error_message:
                task['error_message'] = error_message
            _save_queue(queue)
            logger.info(f"任务完成: {task_id}, success={success}")
            return True
    return False


def get_pending_count() -> int:
    """获取待执行任务数量"""
    queue = _get_queue()
    return sum(1 for t in queue if t['status'] == QUEUE_STATUS_PENDING)


def get_queue_status() -> Dict[str, int]:
    """
    获取队列状态统计
    
    Returns:
        各状态的任务数量
    """
    queue = _get_queue()
    status_count = {
        QUEUE_STATUS_PENDING: 0,
        QUEUE_STATUS_RUNNING: 0,
        QUEUE_STATUS_COMPLETED: 0,
        QUEUE_STATUS_ERROR: 0,
    }
    for task in queue:
        status = task.get('status', QUEUE_STATUS_PENDING)
        if status in status_count:
            status_count[status] += 1
    return status_count


def get_pending_tasks() -> List[Dict[str, Any]]:
    """获取所有待执行的任务"""
    queue = _get_queue()
    return [t for t in queue if t['status'] == QUEUE_STATUS_PENDING]


def get_all_tasks() -> List[Dict[str, Any]]:
    """获取所有任务"""
    return _get_queue().copy()


def clear_completed_tasks() -> int:
    """
    清除已完成和失败的任务
    
    Returns:
        清除的任务数量
    """
    queue = _get_queue()
    original_count = len(queue)
    queue = [t for t in queue if t['status'] in (QUEUE_STATUS_PENDING, QUEUE_STATUS_RUNNING)]
    _save_queue(queue)
    cleared = original_count - len(queue)
    logger.info(f"清除了 {cleared} 个已完成/失败的任务")
    return cleared


def get_source_display_name(source: str) -> str:
    """获取来源的显示名称"""
    source_names = {
        SOURCE_MANUAL: '手动填写',
        SOURCE_TWEET_TOPICS: '推文主题',
        SOURCE_HOTSPOTS: '全网热点',
        SOURCE_NEWS: '新闻资讯',
    }
    return source_names.get(source, source)


def get_status_display(status: str) -> tuple:
    """
    获取状态的显示信息
    
    Returns:
        (显示文本, 颜色)
    """
    status_info = {
        QUEUE_STATUS_PENDING: ('⏳ 等待中', 'gray'),
        QUEUE_STATUS_RUNNING: ('🔄 执行中', 'blue'),
        QUEUE_STATUS_COMPLETED: ('✅ 已完成', 'green'),
        QUEUE_STATUS_ERROR: ('❌ 失败', 'red'),
    }
    return status_info.get(status, ('未知', 'gray'))
