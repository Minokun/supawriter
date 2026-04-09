# -*- coding: utf-8 -*-
"""
Batch Generation Service
批量生成服务
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from backend.api.db.session import get_async_db_session
from backend.api.db.models.batch import BatchJob, BatchTask
from backend.api.core.redis_client import redis_client

logger = logging.getLogger(__name__)


class BatchService:
    """批量生成服务"""

    async def create_batch_job(
        self,
        user_id: int,
        name: str,
        topics: List[str],
        platform: str,
        style_id: Optional[str] = None,
        concurrency: int = 3,
        generate_images: bool = False
    ) -> BatchJob:
        """
        创建批量生成任务

        Args:
            user_id: 用户ID
            name: 任务名称
            topics: 主题列表
            platform: 目标平台
            style_id: 风格ID（可选）
            concurrency: 并发数
            generate_images: 是否生成图片

        Returns:
            创建的BatchJob对象
        """
        async with get_async_db_session() as session:
            # 创建主任务
            job = BatchJob(
                id=uuid4(),
                user_id=user_id,
                name=name,
                topics=topics,
                platform=platform,
                style_id=style_id,
                status='pending',
                total_count=len(topics),
                completed_count=0,
                failed_count=0,
                concurrency=concurrency,
                generate_images=generate_images,
                created_at=datetime.now(timezone.utc)
            )
            session.add(job)
            await session.flush()  # 获取job.id

            # 创建子任务
            for topic in topics:
                task = BatchTask(
                    id=uuid4(),
                    job_id=job.id,
                    topic=topic,
                    status='pending'
                )
                session.add(task)

            await session.commit()
            logger.info(f"Created batch job {job.id} for user {user_id} with {len(topics)} topics")
            return job

    async def start_batch_job(self, job_id: UUID) -> bool:
        """
        启动批量任务（提交ARQ任务）

        Args:
            job_id: 任务ID

        Returns:
            是否成功启动
        """
        try:
            # 更新任务状态为running
            async with get_async_db_session() as session:
                result = await session.execute(
                    update(BatchJob)
                    .where(BatchJob.id == job_id)
                    .values(
                        status='running',
                        started_at=datetime.now(timezone.utc)
                    )
                )
                if result.rowcount == 0:
                    logger.warning(f"Batch job {job_id} not found")
                    return False
                await session.commit()

            # 提交ARQ任务
            from arq import create_pool
            from backend.api.workers.worker_settings import redis_settings

            redis = await create_pool(redis_settings)
            await redis.enqueue_job(
                'process_batch_job',
                str(job_id)
            )
            await redis.close()

            logger.info(f"Started batch job {job_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to start batch job {job_id}: {e}")
            return False

    async def get_job_status(self, job_id: UUID) -> Optional[Dict[str, Any]]:
        """
        获取任务状态（包含进度）

        Args:
            job_id: 任务ID

        Returns:
            任务状态字典
        """
        async with get_async_db_session() as session:
            result = await session.execute(
                select(BatchJob)
                .where(BatchJob.id == job_id)
                .options(selectinload(BatchJob.tasks))
            )
            job = result.scalar_one_or_none()

            if not job:
                return None

            # 计算进度
            progress = 0
            if job.total_count > 0:
                progress = int((job.completed_count / job.total_count) * 100)

            return {
                'id': str(job.id),
                'name': job.name,
                'status': job.status,
                'total_count': job.total_count,
                'completed_count': job.completed_count,
                'failed_count': job.failed_count,
                'progress': progress,
                'platform': job.platform,
                'concurrency': job.concurrency,
                'generate_images': job.generate_images,
                'zip_url': job.zip_url,
                'created_at': job.created_at.isoformat() if job.created_at else None,
                'started_at': job.started_at.isoformat() if job.started_at else None,
                'completed_at': job.completed_at.isoformat() if job.completed_at else None,
                'tasks': [
                    {
                        'id': str(task.id),
                        'topic': task.topic,
                        'status': task.status,
                        'article_id': str(task.article_id) if task.article_id else None,
                        'error_message': task.error_message,
                        'started_at': task.started_at.isoformat() if task.started_at else None,
                        'completed_at': task.completed_at.isoformat() if task.completed_at else None,
                    }
                    for task in job.tasks
                ]
            }

    async def retry_failed_tasks(self, job_id: UUID) -> int:
        """
        重试失败的任务

        Args:
            job_id: 任务ID

        Returns:
            重试的任务数量
        """
        async with get_async_db_session() as session:
            # 获取失败的任务
            result = await session.execute(
                select(BatchTask)
                .where(
                    BatchTask.job_id == job_id,
                    BatchTask.status == 'failed'
                )
            )
            failed_tasks = result.scalars().all()

            if not failed_tasks:
                return 0

            # 重置任务状态
            retry_count = 0
            for task in failed_tasks:
                task.status = 'pending'
                task.error_message = None
                retry_count += 1

            # 更新主任务状态
            await session.execute(
                update(BatchJob)
                .where(BatchJob.id == job_id)
                .values(status='running')
            )

            await session.commit()

            # 重新提交ARQ任务
            from arq import create_pool
            from backend.api.workers.worker_settings import redis_settings

            redis = await create_pool(redis_settings)
            await redis.enqueue_job(
                'process_batch_job',
                str(job_id)
            )
            await redis.close()

            logger.info(f"Retried {retry_count} failed tasks for job {job_id}")
            return retry_count

    async def generate_zip(self, job_id: UUID) -> Optional[str]:
        """
        生成ZIP文件

        Args:
            job_id: 任务ID

        Returns:
            ZIP文件URL或None
        """
        import io
        import zipfile
        import os
        from backend.api.config import settings

        async with get_async_db_session() as session:
            result = await session.execute(
                select(BatchJob)
                .where(BatchJob.id == job_id)
                .options(selectinload(BatchJob.tasks))
            )
            job = result.scalar_one_or_none()

            if not job or job.status != 'completed':
                logger.warning(f"Cannot generate ZIP for job {job_id}: not completed")
                return None

            # 收集所有完成的文章
            articles = []
            for task in job.tasks:
                if task.article_id and task.status == 'completed':
                    # 获取文章内容
                    article_result = await session.execute(
                        select("Article").where("Article.id" == task.article_id)
                    )
                    article = article_result.scalar_one_or_none()
                    if article:
                        articles.append({
                            'title': article.title,
                            'content': article.content,
                            'topic': task.topic
                        })

            if not articles:
                logger.warning(f"No articles to zip for job {job_id}")
                return None

            # 创建ZIP文件
            buffer = io.BytesIO()
            with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
                for i, article in enumerate(articles, 1):
                    filename = f"{i:03d}_{article['title'][:50]}.md"
                    content = f"# {article['title']}\n\n{article['content']}"
                    zf.writestr(filename, content)

            # 保存到本地或上传到存储服务
            zip_filename = f"batch_{job_id}.zip"
            zip_path = os.path.join(settings.UPLOAD_DIR or 'uploads', zip_filename)

            os.makedirs(os.path.dirname(zip_path), exist_ok=True)
            with open(zip_path, 'wb') as f:
                f.write(buffer.getvalue())

            # 更新job的zip_url
            zip_url = f"/api/v1/batch/jobs/{job_id}/download"
            job.zip_url = zip_url
            await session.commit()

            logger.info(f"Generated ZIP for job {job_id}: {zip_path}")
            return zip_url

    async def cancel_job(self, job_id: UUID) -> bool:
        """
        取消进行中的任务

        Args:
            job_id: 任务ID

        Returns:
            是否成功取消
        """
        async with get_async_db_session() as session:
            result = await session.execute(
                select(BatchJob).where(BatchJob.id == job_id)
            )
            job = result.scalar_one_or_none()

            if not job:
                return False

            if job.status not in ['pending', 'running']:
                logger.warning(f"Cannot cancel job {job_id}: status is {job.status}")
                return False

            job.status = 'cancelled'
            job.completed_at = datetime.now(timezone.utc)
            await session.commit()

            logger.info(f"Cancelled batch job {job_id}")
            return True

    async def list_user_jobs(
        self,
        user_id: int,
        page: int = 1,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        获取用户的批量任务列表

        Args:
            user_id: 用户ID
            page: 页码
            limit: 每页数量

        Returns:
            任务列表和分页信息
        """
        async with get_async_db_session() as session:
            # 获取总数
            count_result = await session.execute(
                select(BatchJob).where(BatchJob.user_id == user_id)
            )
            total = len(count_result.scalars().all())

            # 获取分页数据
            result = await session.execute(
                select(BatchJob)
                .where(BatchJob.user_id == user_id)
                .order_by(BatchJob.created_at.desc())
                .offset((page - 1) * limit)
                .limit(limit)
            )
            jobs = result.scalars().all()

            return {
                'items': [
                    {
                        'id': str(job.id),
                        'name': job.name,
                        'status': job.status,
                        'total_count': job.total_count,
                        'completed_count': job.completed_count,
                        'failed_count': job.failed_count,
                        'progress': int((job.completed_count / job.total_count) * 100) if job.total_count > 0 else 0,
                        'platform': job.platform,
                        'zip_url': job.zip_url,
                        'created_at': job.created_at.isoformat() if job.created_at else None,
                    }
                    for job in jobs
                ],
                'total': total,
                'page': page,
                'limit': limit,
                'pages': (total + limit - 1) // limit
            }


# 全局实例
batch_service = BatchService()
