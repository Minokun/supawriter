"""Quota check middleware for API endpoints."""
from typing import Optional, List
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from backend.api.services.quota import QuotaService


class QuotaCheckMiddleware(BaseHTTPMiddleware):
    """
    Quota check middleware for FastAPI.

    Checks if a user has sufficient quota before processing quota-consuming
    operations (e.g., article generation, file uploads, API calls).

    Unlike RateLimitMiddleware which is for short-term rate limiting,
    this middleware is for checking against longer-term quota limits
    (daily/monthly) and consuming quota on successful operations.
    """

    def __init__(
        self,
        app: ASGIApp,
        quota_service: QuotaService,
        quota_type: str,
        quota_amount: int = 1,
        quota_period: str = "daily",
        exclude_paths: Optional[List[str]] = None,
        amount_attr: Optional[str] = None,
        consume_on_success: bool = True
    ):
        """
        Initialize quota check middleware.

        Args:
            app: ASGI application
            quota_service: Quota service instance
            quota_type: Type of quota (article_generation, api_call, storage)
            quota_amount: Amount of quota to check/consume
            quota_period: Period (daily, monthly)
            exclude_paths: Paths to exclude from quota checking
            amount_attr: Request state attribute to get dynamic amount from
                         (e.g., "file_size_mb" for storage uploads)
            consume_on_success: Whether to consume quota on successful request
        """
        super().__init__(app)
        self.quota_service = quota_service
        self.quota_type = quota_type
        self.quota_amount = quota_amount
        self.quota_period = quota_period
        self.exclude_paths = set(exclude_paths or [])
        self.amount_attr = amount_attr
        self.consume_on_success = consume_on_success

    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Process request through quota check middleware.

        Args:
            request: Incoming request
            call_next: Next middleware/handler in chain

        Returns:
            HTTP response
        """
        # Skip excluded paths
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)

        # Skip quota check for unauthenticated users
        if not hasattr(request.state, 'user_id') or not request.state.user_id:
            return await call_next(request)

        user_id = request.state.user_id

        # Get the quota amount (either fixed or from request state)
        amount = self._get_quota_amount(request)

        # Check if quota is available
        quota_available = await self.quota_service.check_quota_available(
            user_id=user_id,
            quota_type=self.quota_type,
            amount=amount,
            period=self.quota_period
        )

        if not quota_available:
            # Get remaining quota for error message
            remaining = await self.quota_service.get_quota_remaining(
                user_id, self.quota_type, self.quota_period
            )

            return JSONResponse(
                status_code=429,
                content={
                    "error": "Quota exceeded",
                    "quota_type": self.quota_type,
                    "period": self.quota_period,
                    "remaining": remaining,
                    "message": (
                        f"You have exceeded your {self.quota_type} quota "
                        f"for the {self.quota_period} period. "
                        f"Remaining: {remaining}."
                    )
                }
            )

        # Process the request
        response = await call_next(request)

        # Consume quota on successful response
        if self.consume_on_success and 200 <= response.status_code < 300:
            await self.quota_service.check_and_consume_quota(
                user_id=user_id,
                quota_type=self.quota_type,
                amount=amount,
                period=self.quota_period
            )

            # Add quota headers to response
            remaining = await self.quota_service.get_quota_remaining(
                user_id, self.quota_type, self.quota_period
            )
            response.headers["X-Quota-Type"] = self.quota_type
            response.headers["X-Quota-Period"] = self.quota_period
            response.headers["X-Quota-Remaining"] = str(remaining)

        return response

    def _get_quota_amount(self, request: Request) -> int:
        """
        Get the quota amount for this request.

        Args:
            request: Incoming request

        Returns:
            Quota amount to check/consume
        """
        # If amount_attr is specified, get amount from request state
        if self.amount_attr and hasattr(request.state, self.amount_attr):
            return getattr(request.state, self.amount_attr)

        return self.quota_amount

    async def check_user_quota(
        self,
        user_id: int,
        amount: Optional[int] = None
    ) -> bool:
        """
        Check if a user has quota available.

        Args:
            user_id: User ID
            amount: Amount to check (defaults to configured amount)

        Returns:
            True if quota is available, False otherwise
        """
        if amount is None:
            amount = self.quota_amount

        return await self.quota_service.check_quota_available(
            user_id=user_id,
            quota_type=self.quota_type,
            amount=amount,
            period=self.quota_period
        )

    async def get_user_quota_status(self, user_id: int) -> dict:
        """
        Get quota status for a user.

        Args:
            user_id: User ID

        Returns:
            Dictionary with quota status information
        """
        remaining = await self.quota_service.get_quota_remaining(
            user_id, self.quota_type, self.quota_period
        )

        quota_info = await self.quota_service.get_user_quota_info(user_id)

        limit = 0
        if quota_info:
            # Map quota_type to the appropriate limit field
            limit_map = {
                "article_generation": f"article_{self.quota_period}_limit",
                "api_call": f"api_{self.quota_period}_limit",
                "storage": "storage_limit_mb",
            }
            limit_field = limit_map.get(self.quota_type)
            if limit_field:
                limit = quota_info.get(limit_field, 0)

        return {
            "quota_type": self.quota_type,
            "period": self.quota_period,
            "limit": limit,
            "remaining": remaining,
            "used": limit - remaining if limit > 0 else 0,
        }
