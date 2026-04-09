"""Alert and notification API routes."""
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select

from backend.api.core.dependencies import get_current_user, get_db as get_db_session
from backend.api.services.alert_service import AlertService
from backend.api.services.analytics_service import AnalyticsService
from backend.api.services.tier_service import TierService
from backend.api.db.models.alert import AlertRecord

router = APIRouter(prefix="/alerts", tags=["alerts"])


# ============ Pydantic Models ============

class KeywordCreate(BaseModel):
    keyword: str = Field(..., min_length=1, max_length=100, description="关键词")
    category: Optional[str] = Field(None, max_length=50, description="分类")


class KeywordResponse(BaseModel):
    id: UUID
    keyword: str
    category: Optional[str]
    is_active: bool
    created_at: str

    class Config:
        from_attributes = True


class KeywordsListResponse(BaseModel):
    keywords: List[KeywordResponse]


class ToggleRequest(BaseModel):
    is_active: bool


class SuggestKeywordsResponse(BaseModel):
    keywords: List[str]


class NotificationResponse(BaseModel):
    id: UUID
    keyword: str
    hotspot_title: str
    hotspot_source: str
    hotspot_url: Optional[str]
    matched_at: str
    is_read: bool

    class Config:
        from_attributes = True


class NotificationsListResponse(BaseModel):
    notifications: List[NotificationResponse]
    total: int
    unread_count: int


class UnreadCountResponse(BaseModel):
    count: int


class MessageResponse(BaseModel):
    message: str


class ReadAllResponse(BaseModel):
    message: str
    count: int


# ============ Alert Keywords Routes ============

@router.get("/keywords", response_model=KeywordsListResponse)
async def get_keywords(
    current_user_id: int = Depends(get_current_user),
    session = Depends(get_db_session)
):
    """Get all alert keywords for current user."""
    service = AlertService(session)
    keywords = await service.get_user_keywords(current_user_id)

    return KeywordsListResponse(
        keywords=[
            KeywordResponse(
                id=k.id,
                keyword=k.keyword,
                category=k.category,
                is_active=k.is_active,
                created_at=k.created_at.isoformat()
            )
            for k in keywords
        ]
    )


@router.post("/keywords", response_model=KeywordResponse)
async def create_keyword(
    data: KeywordCreate,
    current_user_id: int = Depends(get_current_user),
    session = Depends(get_db_session)
):
    """Add a new alert keyword."""
    # Check keyword limit based on tier
    tier = TierService.get_user_tier(current_user_id)

    service = AlertService(session)
    current_count = await service.get_keyword_count(current_user_id)

    # Get limit for tier
    limits = {"free": 1, "pro": 5, "ultra": 999, "superuser": 999}
    limit = limits.get(tier, 1)

    if current_count >= limit:
        raise HTTPException(
            status_code=403,
            detail=f"Your plan allows maximum {limit} keywords. Upgrade to add more."
        )

    keyword = await service.add_keyword(
        current_user_id,
        data.keyword,
        data.category
    )

    return KeywordResponse(
        id=keyword.id,
        keyword=keyword.keyword,
        category=keyword.category,
        is_active=keyword.is_active,
        created_at=keyword.created_at.isoformat()
    )


@router.delete("/keywords/{keyword_id}", response_model=MessageResponse)
async def delete_keyword(
    keyword_id: UUID,
    current_user_id: int = Depends(get_current_user),
    session = Depends(get_db_session)
):
    """Delete an alert keyword."""
    service = AlertService(session)

    # Verify ownership
    keywords = await service.get_user_keywords(current_user_id)
    if not any(k.id == keyword_id for k in keywords):
        raise HTTPException(status_code=404, detail="Keyword not found")

    success = await service.remove_keyword(keyword_id)
    if not success:
        raise HTTPException(status_code=404, detail="Keyword not found")

    return MessageResponse(message="deleted")


@router.put("/keywords/{keyword_id}/toggle", response_model=KeywordResponse)
async def toggle_keyword(
    keyword_id: UUID,
    data: ToggleRequest,
    current_user_id: int = Depends(get_current_user),
    session = Depends(get_db_session)
):
    """Toggle keyword active status."""
    service = AlertService(session)

    # Verify ownership
    keywords = await service.get_user_keywords(current_user_id)
    if not any(k.id == keyword_id for k in keywords):
        raise HTTPException(status_code=404, detail="Keyword not found")

    keyword = await service.toggle_keyword(keyword_id, data.is_active)
    if not keyword:
        raise HTTPException(status_code=404, detail="Keyword not found")

    return KeywordResponse(
        id=keyword.id,
        keyword=keyword.keyword,
        category=keyword.category,
        is_active=keyword.is_active,
        created_at=keyword.created_at.isoformat()
    )


@router.get("/suggest-keywords", response_model=SuggestKeywordsResponse)
async def suggest_keywords(
    current_user_id: int = Depends(get_current_user),
    session = Depends(get_db_session)
):
    """Get AI-suggested keywords based on article history."""
    service = AlertService(session)
    keywords = await service.suggest_keywords(current_user_id)

    return SuggestKeywordsResponse(keywords=keywords)


# ============ Notifications Routes ============

@router.get("/notifications", response_model=NotificationsListResponse)
async def get_notifications(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user_id: int = Depends(get_current_user),
    session = Depends(get_db_session)
):
    """Get paginated notifications for current user."""
    service = AlertService(session)

    notifications = await service.get_notifications(current_user_id, page, limit)
    unread_count = await service.get_unread_count(current_user_id)

    # Get total count
    total = await service.record_repo.count({"user_id": current_user_id})

    # Build response with keyword info
    result_notifications = []
    for n in notifications:
        # Get keyword text
        keyword = await service.keyword_repo.get_by_id(n.keyword_id)
        keyword_text = keyword.keyword if keyword else "Unknown"

        result_notifications.append(NotificationResponse(
            id=n.id,
            keyword=keyword_text,
            hotspot_title=n.hotspot_title,
            hotspot_source=n.hotspot_source,
            hotspot_url=n.hotspot_url,
            matched_at=n.matched_at.isoformat(),
            is_read=n.is_read
        ))

    return NotificationsListResponse(
        notifications=result_notifications,
        total=total,
        unread_count=unread_count
    )


@router.get("/notifications/unread-count", response_model=UnreadCountResponse)
async def get_unread_count(
    current_user_id: int = Depends(get_current_user),
    session = Depends(get_db_session)
):
    """Get unread notification count."""
    service = AlertService(session)
    count = await service.get_unread_count(current_user_id)

    return UnreadCountResponse(count=count)


@router.put("/notifications/{notification_id}/read", response_model=NotificationResponse)
async def mark_notification_read(
    notification_id: UUID,
    current_user_id: int = Depends(get_current_user),
    session = Depends(get_db_session)
):
    """Mark a notification as read."""
    service = AlertService(session)

    # Verify ownership - direct DB query for better performance
    result = await session.execute(
        select(AlertRecord).where(
            AlertRecord.id == notification_id,
            AlertRecord.user_id == current_user_id
        )
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Notification not found")

    notification = await service.mark_as_read(notification_id)
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")

    # Get keyword text
    keyword = await service.keyword_repo.get_by_id(notification.keyword_id)
    keyword_text = keyword.keyword if keyword else "Unknown"

    return NotificationResponse(
        id=notification.id,
        keyword=keyword_text,
        hotspot_title=notification.hotspot_title,
        hotspot_source=notification.hotspot_source,
        hotspot_url=notification.hotspot_url,
        matched_at=notification.matched_at.isoformat(),
        is_read=notification.is_read
    )


@router.put("/notifications/read-all", response_model=ReadAllResponse)
async def mark_all_read(
    current_user_id: int = Depends(get_current_user),
    session = Depends(get_db_session)
):
    """Mark all notifications as read."""
    service = AlertService(session)
    count = await service.mark_all_read(current_user_id)

    return ReadAllResponse(message="all marked as read", count=count)


@router.delete("/notifications/{notification_id}", response_model=MessageResponse)
async def delete_notification(
    notification_id: UUID,
    current_user_id: int = Depends(get_current_user),
    session = Depends(get_db_session)
):
    """Delete a notification."""
    service = AlertService(session)

    # Verify ownership - direct DB query for better performance
    result = await session.execute(
        select(AlertRecord).where(
            AlertRecord.id == notification_id,
            AlertRecord.user_id == current_user_id
        )
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Notification not found")

    success = await service.delete_notification(notification_id)
    if not success:
        raise HTTPException(status_code=404, detail="Notification not found")

    return MessageResponse(message="deleted")
