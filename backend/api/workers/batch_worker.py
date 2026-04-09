# -*- coding: utf-8 -*-
"""
Batch Generation Worker
批量生成Worker
"""

import asyncio
import logging
from typing import Dict, Any, List
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from backend.api.db.session import get_async_db_session
from backend.api.db.models.batch import BatchJob, BatchTask
from backend.api.workers.progress import ProgressTracker

logger = logging.getLogger(__name__)


async def process_batch_job(ctx, job_id: str) -> Dict[str, Any]:
    """
    ARQ任务：处理批量生成任务

    流程:
    1. 获取任务配置
    2. 创建子任务（每个主题一个）
    3. 并发执行（使用asyncio.Semaphore控制并发）
    4. 更新进度
    5. 生成ZIP（如果全部完成）

    Args:
        ctx: ARQ context
        job_id: 任务ID (字符串)

    Returns:
        执行结果
    """
    logger.info("=" * 60)
    logger.info(f"Starting batch job processing: {job_id}")
    logger.info("=" * 60)

    stats = {
        'total': 0,
        'completed': 0,
        'failed': 0,
        'errors': []
    }

    try:
        job_uuid = UUID(job_id)

        async with get_async_db_session() as session:
            # 获取任务配置
            result = await session.execute(
                select(BatchJob)
                .where(BatchJob.id == job_uuid)
                .options(selectinload(BatchJob.tasks))
            )
            job = result.scalar_one_or_none()

            if not job:
                logger.error(f"Batch job {job_id} not found")
                return {'success': False, 'error': 'Job not found'}

            if job.status == 'cancelled':
                logger.info(f"Batch job {job_id} was cancelled")
                return {'success': True, 'status': 'cancelled'}

            stats['total'] = len(job.tasks)
            concurrency = job.concurrency or 3

            # 创建信号量控制并发
            semaphore = asyncio.Semaphore(concurrency)

            async def process_task_with_limit(task: BatchTask) -> Dict[str, Any]:
                """带并发限制的任务处理"""
                async with semaphore:
                    return await generate_single_article(
                        task_id=str(task.id),
                        topic=task.topic,
                        platform=job.platform,
                        style_id=job.style_id,
                        generate_images=job.generate_images,
                        user_id=job.user_id
                    )

            # 并发执行所有任务
            logger.info(f"Processing {len(job.tasks)} tasks with concurrency={concurrency}")
            task_results = await asyncio.gather(*[
                process_task_with_limit(task)
                for task in job.tasks
                if task.status == 'pending'  # 只处理pending状态的任务
            ], return_exceptions=True)

            # 统计结果
            for i, result in enumerate(task_results):
                if isinstance(result, Exception):
                    stats['failed'] += 1
                    stats['errors'].append(str(result))
                    logger.error(f"Task {i} failed with exception: {result}")
                elif result.get('success'):
                    stats['completed'] += 1
                else:
                    stats['failed'] += 1
                    stats['errors'].append(result.get('error', 'Unknown error'))

            # 更新任务状态
            job.completed_count = stats['completed']
            job.failed_count = stats['failed']

            if stats['failed'] == 0:
                job.status = 'completed'
            elif stats['completed'] == 0:
                job.status = 'failed'
            else:
                job.status = 'partial'

            job.completed_at = datetime.now(timezone.utc)
            await session.commit()

            # 如果全部完成，触发ZIP生成
            if job.status == 'completed':
                try:
                    from backend.api.services.batch_service import batch_service
                    await batch_service.generate_zip(job_uuid)
                except Exception as e:
                    logger.error(f"Failed to generate ZIP for job {job_id}: {e}")

            logger.info("=" * 60)
            logger.info(f"Batch job {job_id} completed: {stats}")
            logger.info("=" * 60)

            return {
                'success': True,
                'job_id': job_id,
                'stats': stats
            }

    except Exception as e:
        logger.exception(f"Fatal error in process_batch_job: {e}")
        return {
            'success': False,
            'error': str(e),
            'stats': stats
        }


async def generate_single_article(
    task_id: str,
    topic: str,
    platform: str,
    style_id: str = None,
    generate_images: bool = False,
    user_id: int = None
) -> Dict[str, Any]:
    """
    生成单篇文章

    复用现有的 article_worker 逻辑

    Args:
        task_id: 子任务ID
        topic: 主题
        platform: 目标平台
        style_id: 风格ID
        generate_images: 是否生成图片
        user_id: 用户ID

    Returns:
        生成结果
    """
    task_uuid = UUID(task_id)

    try:
        # 更新任务状态为running
        async with get_async_db_session() as session:
            result = await session.execute(
                select(BatchTask).where(BatchTask.id == task_uuid)
            )
            task = result.scalar_one_or_none()

            if not task:
                return {'success': False, 'error': 'Task not found'}

            task.status = 'running'
            task.started_at = datetime.now(timezone.utc)
            await session.commit()

        logger.info(f"Generating article for task {task_id}: {topic}")

        # 调用article_worker生成文章
        from backend.api.workers.article_worker import generate_article_task
        from backend.api.utils.searxng_compat import set_user_context

        # 设置用户上下文
        if user_id:
            set_user_context(user_id)

        # 生成文章
        article_result = await generate_article_task(
            None,  # ctx
            task_id=task_id,
            topic=topic,
            user_id=user_id,
            custom_style="",  # 可以从style_id加载风格
            spider_num=None,
            extra_urls=None,
            model_type="deepseek",
            model_name="deepseek-chat"
        )

        # 更新任务状态
        async with get_async_db_session() as session:
            result = await session.execute(
                select(BatchTask).where(BatchTask.id == task_uuid)
            )
            task = result.scalar_one_or_none()

            if article_result.get('success'):
                task.status = 'completed'
                task.article_id = UUID(article_result['article_id']) if article_result.get('article_id') else None
                logger.info(f"Task {task_id} completed successfully")
            else:
                task.status = 'failed'
                task.error_message = article_result.get('error', 'Unknown error')
                logger.error(f"Task {task_id} failed: {task.error_message}")

            task.completed_at = datetime.now(timezone.utc)
            await session.commit()

        return article_result

    except Exception as e:
        logger.exception(f"Error generating article for task {task_id}: {e}")

        # 更新任务状态为failed
        try:
            async with get_async_db_session() as session:
                result = await session.execute(
                    select(BatchTask).where(BatchTask.id == task_uuid)
                )
                task = result.scalar_one_or_none()
                if task:
                    task.status = 'failed'
                    task.error_message = str(e)
                    task.completed_at = datetime.now(timezone.utc)
                    await session.commit()
        except Exception as db_error:
            logger.error(f"Failed to update task status: {db_error}")

        return {'success': False, 'error': str(e)}
