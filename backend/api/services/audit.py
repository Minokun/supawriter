"""Audit service for logging and querying audit logs."""
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Dict, List, Any
from datetime import datetime, timezone, timedelta
from backend.api.repositories.audit import AuditLogRepository


class AuditService:
    """
    Service layer for audit log management.

    Handles logging of user actions, API calls, and security events
    for compliance and auditing purposes.
    """

    def __init__(self, session: AsyncSession, audit_repository: AuditLogRepository):
        """
        Initialize AuditService.

        Args:
            session: Database session
            audit_repository: Audit log repository instance
        """
        self.session = session
        self.audit_repo = audit_repository

    async def log_action(
        self,
        user_id: Optional[int],
        action: str,
        resource: str,
        status_code: int,
        ip_address: Optional[str] = None,
        request_headers: Optional[Dict[str, str]] = None,
        request_body: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log an action to the audit log.

        Args:
            user_id: User ID (None for anonymous requests)
            action: Action performed (e.g., HTTP method, custom action)
            resource: Resource affected (e.g., endpoint path, resource ID)
            status_code: HTTP status code
            ip_address: Client IP address
            request_headers: Request headers (if logging enabled)
            request_body: Request body (if logging enabled)
            metadata: Additional metadata
        """
        # Build request_data dict from headers, body, and metadata
        request_data = {}
        if request_headers:
            request_data["headers"] = request_headers
        if request_body:
            request_data["body"] = request_body
        if metadata:
            request_data["metadata"] = metadata

        # Determine resource_type and resource_id from resource string
        # For endpoint paths, resource_type is "api" and the path goes in resource_id
        # For custom resources, try to parse type:id format
        resource_type = "api"
        resource_id = resource

        if ":" in str(resource):
            parts = str(resource).split(":", 1)
            if len(parts) == 2:
                resource_type = parts[0]
                resource_id = parts[1]

        # Get user agent from metadata if available
        user_agent = None
        if metadata and "user_agent" in metadata:
            user_agent = metadata["user_agent"]

        await self.audit_repo.create_log(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            request_data=request_data if request_data else None,
            response_status=status_code
        )

    async def get_user_logs(
        self,
        user_id: int,
        limit: int = 100
    ) -> List[Any]:
        """
        Get audit logs for a specific user.

        Args:
            user_id: User ID
            limit: Maximum number of logs to return

        Returns:
            List of audit log entries
        """
        return await self.audit_repo.list(
            filters={"user_id": user_id},
            limit=limit
        )

    async def get_resource_logs(
        self,
        resource: str,
        limit: int = 100
    ) -> List[Any]:
        """
        Get audit logs for a specific resource.

        Args:
            resource: Resource path or ID
            limit: Maximum number of logs to return

        Returns:
            List of audit log entries
        """
        return await self.audit_repo.list(
            filters={"resource": resource},
            limit=limit
        )

    async def get_logs_by_action(
        self,
        action: str,
        limit: int = 100
    ) -> List[Any]:
        """
        Get audit logs by action type.

        Args:
            action: Action type (e.g., "POST", "DELETE")
            limit: Maximum number of logs to return

        Returns:
            List of audit log entries
        """
        return await self.audit_repo.list(
            filters={"action": action},
            limit=limit
        )

    async def get_logs_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        limit: int = 1000
    ) -> List[Any]:
        """
        Get audit logs within a date range.

        Args:
            start_date: Start of date range
            end_date: End of date range
            limit: Maximum number of logs to return

        Returns:
            List of audit log entries
        """
        return await self.audit_repo.list(
            filters={
                "created_at_gte": start_date,
                "created_at_lte": end_date
            },
            limit=limit
        )

    async def get_failed_requests(
        self,
        hours: int = 24,
        limit: int = 100
    ) -> List[Any]:
        """
        Get failed requests (4xx and 5xx status codes).

        Args:
            hours: Number of hours to look back
            limit: Maximum number of logs to return

        Returns:
            List of failed request audit logs
        """
        start_date = datetime.now(timezone.utc) - timedelta(hours=hours)
        return await self.audit_repo.list(
            filters={
                "created_at_gte": start_date,
                "status_code_gte": 400
            },
            limit=limit
        )

    async def get_security_events(
        self,
        hours: int = 24,
        limit: int = 100
    ) -> List[Any]:
        """
        Get security-related events (authentication failures, etc.).

        Args:
            hours: Number of hours to look back
            limit: Maximum number of logs to return

        Returns:
            List of security event audit logs
        """
        # Get login/auth failures
        start_date = datetime.now(timezone.utc) - timedelta(hours=hours)
        return await self.audit_repo.list(
            filters={
                "created_at_gte": start_date,
                "action": "login",
                "status_code_gte": 400
            },
            limit=limit
        )

    async def get_audit_summary(
        self,
        user_id: Optional[int] = None,
        hours: int = 24
    ) -> Dict[str, Any]:
        """
        Get a summary of audit activity.

        Args:
            user_id: Optional user ID to filter by
            hours: Number of hours to look back

        Returns:
            Dictionary with audit summary statistics
        """
        start_date = datetime.now(timezone.utc) - timedelta(hours=hours)

        filters = {"created_at_gte": start_date}
        if user_id:
            filters["user_id"] = user_id

        logs = await self.audit_repo.list(filters=filters, limit=10000)

        # Calculate statistics
        total_requests = len(logs)
        successful_requests = sum(1 for log in logs if 200 <= log.status_code < 300)
        failed_requests = sum(1 for log in logs if log.status_code >= 400)

        # Count by action type
        action_counts = {}
        for log in logs:
            action_counts[log.action] = action_counts.get(log.action, 0) + 1

        # Count by resource
        resource_counts = {}
        for log in logs:
            resource_counts[log.resource] = resource_counts.get(log.resource, 0) + 1

        return {
            "period_hours": hours,
            "total_requests": total_requests,
            "successful_requests": successful_requests,
            "failed_requests": failed_requests,
            "success_rate": round(successful_requests / total_requests * 100, 2) if total_requests > 0 else 0,
            "action_counts": action_counts,
            "top_resources": sorted(resource_counts.items(), key=lambda x: x[1], reverse=True)[:10],
        }

    async def cleanup_old_logs(
        self,
        days_to_keep: int = 90
    ) -> int:
        """
        Delete audit logs older than the specified number of days.

        Args:
            days_to_keep: Number of days of logs to keep

        Returns:
            Number of logs deleted
        """
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)
        return await self.audit_repo.delete_old_logs(cutoff_date)
