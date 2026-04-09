# -*- coding: utf-8 -*-
"""
Batch Generation API Routes
批量生成API路由
"""

from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from backend.api.core.dependencies import get_current_user
from backend.api.services.batch_service import batch_service
from backend.api.services.tier_service import TierService

router = APIRouter(prefix="/batch", tags=["batch"])


# ============ Pydantic Models ============

class CreateBatchJobRequest(BaseModel):
    """创建批量任务请求"""
    name: str = Field(..., min_length=1, max_length=200, description="任务名称")
    topics: List[str] = Field(..., min_items=1, description="主题列表")
    platform: str = Field(..., description="目标平台: wechat/zhihu/xiaohongshu")
    style_id: Optional[str] = Field(None, description="风格ID")
    concurrency: int = Field(3, ge=1, le=5, description="并发数")
    generate_images: bool = Field(False, description="是否生成图片")


class BatchTaskResponse(BaseModel):
    """子任务响应"""
    id: str
    topic: str
    status: str
    article_id: Optional[str] = None
    error_message: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class BatchJobResponse(BaseModel):
    """批量任务响应"""
    id: str
    name: str
    status: str
    total_count: int
    completed_count: int
    failed_count: int
    progress: int
    platform: str
    concurrency: int
    generate_images: bool
    zip_url: Optional[str] = None
    created_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    tasks: List[BatchTaskResponse] = []


class BatchJobListResponse(BaseModel):
    """批量任务列表响应"""
    items: List[BatchJobResponse]
    total: int
    page: int
    limit: int
    pages: int


class RetryResponse(BaseModel):
    """重试响应"""
    message: str
    retried_count: int


class CancelResponse(BaseModel):
    """取消响应"""
    message: str


class MessageResponse(BaseModel):
    """通用消息响应"""
    message: str


# ============ Helper Functions ============

def check_batch_quota(user_id: int, topic_count: int):
    """检查批量生成配额"""
    tier = TierService.get_user_tier(user_id)

    # 各等级的批量任务限制
    job_limits = {"free": 3, "pro": 10, "ultra": 999, "superuser": 999}
    topic_limits = {"free": 5, "pro": 20, "ultra": 50, "superuser": 50}

    job_limit = job_limits.get(tier, 3)
    topic_limit = topic_limits.get(tier, 5)

    if topic_count > topic_limit:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Your plan allows maximum {topic_limit} topics per batch. Upgrade to add more."
        )

    return job_limit, topic_limit


async def verify_job_ownership(job_id: UUID, user_id: int) -> dict:
    """验证任务所有权，返回任务状态"""
    job_status = await batch_service.get_job_status(job_id)

    if not job_status:
        raise HTTPException(status_code=404, detail="Job not found")

    # 通过 service 获取的 job_status 包含 user_id 字段
    if job_status.get('user_id') and job_status['user_id'] != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to access this job")

    return job_status


# ============ Batch Job Routes ============

@router.post("/jobs", response_model=BatchJobResponse)
async def create_batch_job(
    request: CreateBatchJobRequest,
    current_user_id: int = Depends(get_current_user)
):
    """
    创建批量生成任务

    - 创建任务和子任务记录
    - 返回任务信息，需要调用 /jobs/{id}/start 启动
    """
    # 检查配额
    check_batch_quota(current_user_id, len(request.topics))

    # 创建任务
    job = await batch_service.create_batch_job(
        user_id=current_user_id,
        name=request.name,
        topics=request.topics,
        platform=request.platform,
        style_id=request.style_id,
        concurrency=request.concurrency,
        generate_images=request.generate_images
    )

    # 自动启动任务
    await batch_service.start_batch_job(job.id)

    # 返回完整状态
    return await batch_service.get_job_status(job.id)


@router.get("/jobs", response_model=BatchJobListResponse)
async def list_batch_jobs(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user_id: int = Depends(get_current_user)
):
    """获取用户的批量任务列表"""
    result = await batch_service.list_user_jobs(
        user_id=current_user_id,
        page=page,
        limit=limit
    )

    return BatchJobListResponse(**result)


@router.get("/jobs/{job_id}", response_model=BatchJobResponse)
async def get_batch_job(
    job_id: UUID,
    current_user_id: int = Depends(get_current_user)
):
    """获取批量任务详情和进度"""
    # 验证权限并获取状态
    job_status = await verify_job_ownership(job_id, current_user_id)

    return BatchJobResponse(**job_status)


@router.post("/jobs/{job_id}/retry", response_model=RetryResponse)
async def retry_batch_job(
    job_id: UUID,
    current_user_id: int = Depends(get_current_user)
):
    """重试失败的任务"""
    # 验证权限
    await verify_job_ownership(job_id, current_user_id)

    # 重试失败任务
    retried_count = await batch_service.retry_failed_tasks(job_id)

    return RetryResponse(
        message=f"Retried {retried_count} failed tasks",
        retried_count=retried_count
    )


@router.post("/jobs/{job_id}/cancel", response_model=CancelResponse)
async def cancel_batch_job(
    job_id: UUID,
    current_user_id: int = Depends(get_current_user)
):
    """取消进行中的批量任务"""
    # 验证权限
    await verify_job_ownership(job_id, current_user_id)

    # 取消任务
    success = await batch_service.cancel_job(job_id)
    if not success:
        raise HTTPException(
            status_code=400,
            detail="Cannot cancel job: already completed or cancelled"
        )

    return CancelResponse(message="Job cancelled successfully")


@router.get("/jobs/{job_id}/download")
async def download_batch_zip(
    job_id: UUID,
    current_user_id: int = Depends(get_current_user)
):
    """
    下载批量生成结果的ZIP文件

    - 只有完成的任务才能下载
    - 如果ZIP未生成，会触发生成
    """
    from fastapi.responses import FileResponse
    import os
    from backend.api.config import settings

    # 验证权限并获取状态
    job_status = await verify_job_ownership(job_id, current_user_id)

    # 检查任务状态
    if job_status['status'] not in ['completed', 'partial']:
        raise HTTPException(
            status_code=400,
            detail="Job not completed yet"
        )

    # 生成ZIP（如果还没有）
    zip_url = job_status.get('zip_url')
    if not zip_url:
        zip_url = await batch_service.generate_zip(job_id)

    if not zip_url:
        raise HTTPException(
            status_code=400,
            detail="No articles available for download"
        )

    # 返回文件
    zip_filename = f"batch_{job_id}.zip"
    zip_path = os.path.join(settings.UPLOAD_DIR or 'uploads', zip_filename)

    if not os.path.exists(zip_path):
        raise HTTPException(status_code=404, detail="ZIP file not found")

    return FileResponse(
        zip_path,
        filename=f"batch_{job_status['name']}_{job_id}.zip",
        media_type="application/zip"
    )


@router.delete("/jobs/{job_id}", response_model=MessageResponse)
async def delete_batch_job(
    job_id: UUID,
    current_user_id: int = Depends(get_current_user)
):
    """删除批量任务"""
    from backend.api.db.session import get_async_db_session
    from backend.api.db.models.batch import BatchJob
    from sqlalchemy import select

    async with get_async_db_session() as session:
        result = await session.execute(
            select(BatchJob).where(BatchJob.id == job_id)
        )
        job = result.scalar_one_or_none()

        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        # 权限检查
        if job.user_id != current_user_id:
            raise HTTPException(status_code=403, detail="Not authorized")

        await session.delete(job)
        await session.commit()

    return MessageResponse(message="Job deleted successfully")
