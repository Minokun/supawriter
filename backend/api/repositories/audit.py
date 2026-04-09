"""Audit log repository with security and compliance operations."""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, delete, func, case
from typing import Optional, List, Dict
from datetime import datetime, timezone, timedelta
from backend.api.db.models.audit import AuditLog
from backend.api.repositories.base import BaseRepository


class AuditLogRepository(BaseRepository[AuditLog]):
    """
    Repository for AuditLog model with security and compliance operations.

    Handles audit logging for user actions, API calls, security events,
    and compliance tracking.
    """

    def __init__(self, session: AsyncSession):
        """Initialize AuditLog repository."""
        super().__init__(session, AuditLog)

    async def create_log(
        self,
        user_id: Optional[int],
        action: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_data: Optional[dict] = None,
        response_status: int = 200,
        error_message: Optional[str] = None
    ) -> AuditLog:
        """
        Create an audit log entry.

        Args:
            user_id: User ID (optional for system actions)
            action: Action performed (e.g., 'user.login', 'article.create')
            resource_type: Type of resource affected
            resource_id: ID of the resource
            ip_address: Client IP address
            user_agent: Client user agent
            request_data: Request data as dictionary
            response_status: HTTP status code
            error_message: Error message if applicable

        Returns:
            Created AuditLog instance
        """
        log = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            request_data=request_data,
            response_status=response_status,
            error_message=error_message
        )
        self.session.add(log)
        await self.session.flush()
        return log

    async def get_by_user(
        self,
        user_id: int,
        offset: int = 0,
        limit: int = 100
    ) -> List[AuditLog]:
        """
        Get audit logs for a specific user.

        Args:
            user_id: User ID
            offset: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of AuditLog instances
        """
        return await self.list(
            filters={"user_id": user_id},
            offset=offset,
            limit=limit,
            order_by="created_at DESC"
        )

    async def get_by_action(
        self,
        action: str,
        offset: int = 0,
        limit: int = 100
    ) -> List[AuditLog]:
        """
        Get audit logs by action type.

        Args:
            action: Action type
            offset: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of AuditLog instances
        """
        return await self.list(
            filters={"action": action},
            offset=offset,
            limit=limit,
            order_by="created_at DESC"
        )

    async def get_by_resource(
        self,
        resource_type: str,
        resource_id: str,
        offset: int = 0,
        limit: int = 100
    ) -> List[AuditLog]:
        """
        Get audit logs for a specific resource.

        Args:
            resource_type: Type of resource
            resource_id: ID of the resource
            offset: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of AuditLog instances
        """
        stmt = select(self.model).where(
            and_(
                self.model.resource_type == resource_type,
                self.model.resource_id == resource_id
            )
        ).order_by(self.model.created_at.desc()).offset(offset).limit(limit)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_failed_requests(
        self,
        offset: int = 0,
        limit: int = 100
    ) -> List[AuditLog]:
        """
        Get all failed request logs (status >= 400).

        Args:
            offset: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of AuditLog instances with failed requests
        """
        stmt = select(self.model).where(
            self.model.response_status >= 400
        ).order_by(self.model.created_at.desc()).offset(offset).limit(limit)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_error_logs(
        self,
        offset: int = 0,
        limit: int = 100
    ) -> List[AuditLog]:
        """
        Get logs with error messages.

        Args:
            offset: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of AuditLog instances with errors
        """
        stmt = select(self.model).where(
            self.model.error_message.is_not(None)
        ).order_by(self.model.created_at.desc()).offset(offset).limit(limit)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_recent_logs(
        self,
        user_id: Optional[int] = None,
        limit: int = 100
    ) -> List[AuditLog]:
        """
        Get recent audit logs.

        Args:
            user_id: Optional user ID to filter by
            limit: Maximum number of records to return

        Returns:
            List of recent AuditLog instances
        """
        if user_id:
            return await self.get_by_user(user_id, limit=limit)

        return await self.get_all(limit=limit, order_by="created_at DESC")

    async def count_by_action(self, action: str) -> int:
        """
        Count audit logs by action type.

        Args:
            action: Action type to count

        Returns:
            Number of logs with this action
        """
        return await self.count(filters={"action": action})

    async def get_logs_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        user_id: Optional[int] = None,
        offset: int = 0,
        limit: int = 100
    ) -> List[AuditLog]:
        """
        Get audit logs within a date range.

        Args:
            start_date: Start of date range
            end_date: End of date range
            user_id: Optional user ID to filter by
            offset: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of AuditLog instances
        """
        stmt = select(self.model).where(
            and_(
                self.model.created_at >= start_date,
                self.model.created_at <= end_date
            )
        )

        if user_id:
            stmt = stmt.where(self.model.user_id == user_id)

        stmt = stmt.order_by(self.model.created_at.desc()).offset(offset).limit(limit)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_user_actions_summary(
        self,
        user_id: int,
        days: int = 30
    ) -> Dict[str, int]:
        """
        Get summary of actions performed by a user.

        Args:
            user_id: User ID
            days: Number of days to look back

        Returns:
            Dictionary with action as key and count as value
        """
        since_date = datetime.now(timezone.utc) - timedelta(days=days)

        stmt = select(
            self.model.action,
            func.count().label('count')
        ).where(
            and_(
                self.model.user_id == user_id,
                self.model.created_at >= since_date
            )
        ).group_by(self.model.action)

        result = await self.session.execute(stmt)
        return {row.action: row.count for row in result.all()}

    async def log_security_event(
        self,
        user_id: Optional[int],
        action: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        details: Optional[dict] = None
    ) -> AuditLog:
        """
        Log a security event.

        Args:
            user_id: User ID
            action: Security action (e.g., 'security.suspicious_login')
            resource_type: Type of resource
            resource_id: ID of the resource
            ip_address: Client IP address
            details: Additional security details

        Returns:
            Created AuditLog instance
        """
        return await self.create_log(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            request_data=details,
            response_status=200
        )

    async def cleanup_old_logs(
        self,
        days: int = 90
    ) -> int:
        """
        Delete audit logs older than specified days.

        Args:
            days: Number of days to keep logs

        Returns:
            Number of logs deleted
        """
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

        stmt = delete(self.model).where(
            self.model.created_at < cutoff_date
        )

        result = await self.session.execute(stmt)
        return result.rowcount

    async def get_security_events(
        self,
        offset: int = 0,
        limit: int = 100
    ) -> List[AuditLog]:
        """
        Get all security-related audit logs.

        Args:
            offset: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of security event AuditLog instances
        """
        stmt = select(self.model).where(
            self.model.action.like('security.%')
        ).order_by(self.model.created_at.desc()).offset(offset).limit(limit)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_failed_logins(
        self,
        hours: int = 24,
        offset: int = 0,
        limit: int = 100
    ) -> List[AuditLog]:
        """
        Get failed login attempts.

        Args:
            hours: Number of hours to look back
            offset: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of failed login AuditLog instances
        """
        since_date = datetime.now(timezone.utc) - timedelta(hours=hours)

        stmt = select(self.model).where(
            and_(
                self.model.action == 'user.login',
                self.model.response_status >= 400,
                self.model.created_at >= since_date
            )
        ).order_by(self.model.created_at.desc()).offset(offset).limit(limit)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_user_login_history(
        self,
        user_id: int,
        limit: int = 50
    ) -> List[AuditLog]:
        """
        Get login history for a user.

        Args:
            user_id: User ID
            limit: Maximum number of records to return

        Returns:
            List of login/logout AuditLog instances
        """
        stmt = select(self.model).where(
            and_(
                self.model.user_id == user_id,
                self.model.action.in_(['user.login', 'user.logout'])
            )
        ).order_by(self.model.created_at.desc()).limit(limit)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_failed_requests_by_user(
        self,
        user_id: int,
        hours: int = 24
    ) -> int:
        """
        Count failed requests for a user in the last N hours.

        Args:
            user_id: User ID
            hours: Number of hours to look back

        Returns:
            Number of failed requests
        """
        since_date = datetime.now(timezone.utc) - timedelta(hours=hours)

        stmt = select(func.count()).select_from(self.model).where(
            and_(
                self.model.user_id == user_id,
                self.model.response_status >= 400,
                self.model.created_at >= since_date
            )
        )

        result = await self.session.execute(stmt)
        return result.scalar() or 0
