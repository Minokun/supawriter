"""Rate limiting middleware for API endpoints."""
from typing import Tuple, Optional, Callable, Awaitable, List
from datetime import datetime, timezone, timedelta
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import logging
from backend.api.services.quota import QuotaService

logger = logging.getLogger(__name__)


class RateLimiterMemory:
    """
    In-memory rate limiter using sliding window algorithm.

    Tracks request timestamps for each key (user_id or IP) and endpoint.
    """

    def __init__(self, window_seconds: int = 60):
        """
        Initialize rate limiter.

        Args:
            window_seconds: Time window in seconds for rate limiting
        """
        self.window_seconds = window_seconds
        # Structure: {key: {endpoint: [timestamp1, timestamp2, ...]}}
        self._requests: dict = {}

    async def is_allowed(
        self,
        key: str,
        endpoint: str,
        limit: int,
        window: int
    ) -> Tuple[bool, int]:
        """
        Check if request is allowed under rate limit.

        Args:
            key: Unique key (user_id or IP address)
            endpoint: API endpoint path
            limit: Maximum requests allowed
            window: Time window in seconds

        Returns:
            Tuple of (allowed: bool, retry_after: int)
        """
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(seconds=window)

        # Get or create request tracking for this key
        if key not in self._requests:
            self._requests[key] = {}

        if endpoint not in self._requests[key]:
            self._requests[key][endpoint] = []

        # Filter out requests outside the window
        requests = self._requests[key][endpoint]
        self._requests[key][endpoint] = [r for r in requests if r > cutoff]

        # Check if under limit (allow up to and including the limit)
        allowed = len(self._requests[key][endpoint]) <= limit

        # Calculate retry_after if not allowed
        retry_after = 0
        if not allowed and len(self._requests[key][endpoint]) > 0:
            oldest_request = self._requests[key][endpoint][0]
            retry_after = int(window - (now - oldest_request).total_seconds())
            retry_after = max(1, retry_after)

        return allowed, retry_after

    async def record_request(
        self,
        key: str,
        endpoint: str,
        timestamp: Optional[datetime] = None
    ):
        """
        Record a request for rate limiting.

        Args:
            key: Unique key (user_id or IP address)
            endpoint: API endpoint path
            timestamp: Request timestamp (defaults to now)
        """
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)

        if key not in self._requests:
            self._requests[key] = {}
        if endpoint not in self._requests[key]:
            self._requests[key][endpoint] = []

        self._requests[key][endpoint].append(timestamp)

    async def reset(self, key: str, endpoint: str):
        """
        Reset rate limit for a key and endpoint.

        Args:
            key: Unique key (user_id or IP address)
            endpoint: API endpoint path
        """
        if key in self._requests and endpoint in self._requests[key]:
            self._requests[key][endpoint] = []

    def get_request_count(self, key: str, endpoint: str) -> int:
        """
        Get current request count for a key and endpoint.

        Args:
            key: Unique key (user_id or IP address)
            endpoint: API endpoint path

        Returns:
            Number of requests in the current window
        """
        if key in self._requests and endpoint in self._requests[key]:
            return len(self._requests[key][endpoint])
        return 0


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware for FastAPI.

    Limits the number of requests per user/IP for API endpoints
    to prevent abuse and ensure fair resource allocation.
    """

    def __init__(
        self,
        app: ASGIApp,
        quota_service: Optional[QuotaService] = None,
        quota_service_factory: Optional[Callable[[], Awaitable[QuotaService]]] = None,
        rate_limiter: Optional[RateLimiterMemory] = None,
        requests_per_minute: int = 60,
        public_endpoints: Optional[List[str]] = None,
        exclude_paths: Optional[List[str]] = None
    ):
        """
        Initialize rate limit middleware.

        Args:
            app: ASGI application
            quota_service: Quota service instance (for static usage)
            quota_service_factory: Async factory to create QuotaService per request
            rate_limiter: Custom rate limiter (defaults to RateLimiterMemory)
            requests_per_minute: Default requests per minute limit
            public_endpoints: List of public endpoint prefixes
            exclude_paths: Paths to exclude from rate limiting
        """
        super().__init__(app)
        self.quota_service = quota_service
        self.quota_service_factory = quota_service_factory
        self.rate_limiter = rate_limiter or RateLimiterMemory()
        self.requests_per_minute = requests_per_minute
        self.public_endpoints = set(public_endpoints or [])
        self.exclude_paths = set(exclude_paths or ["/health", "/metrics", "/docs"])

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request through rate limit middleware.

        Args:
            request: Incoming request
            call_next: Next middleware/handler in chain

        Returns:
            HTTP response
        """
        # Skip excluded paths
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)

        # Determine rate limit key and limit
        key, endpoint, limit = self._get_rate_limit_params(request)

        # Check if allowed
        allowed, retry_after = await self.rate_limiter.is_allowed(
            key, endpoint, limit, 60
        )

        if not allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "retry_after": retry_after,
                    "message": f"Too many requests. Please retry after {retry_after} seconds."
                }
            )

        # Record the request
        await self.rate_limiter.record_request(key, endpoint)

        # Check and consume API quota
        if hasattr(request.state, 'user_id') and request.state.user_id:
            try:
                if self.quota_service:
                    quota_available = await self.quota_service.check_quota_available(
                        request.state.user_id, "api_call", 1, "daily"
                    )
                    if not quota_available:
                        return JSONResponse(
                            status_code=429,
                            content={
                                "error": "API quota exceeded",
                                "message": "You have exceeded your API quota. Please upgrade your plan."
                            }
                        )
                elif self.quota_service_factory:
                    # Use factory as async context manager to keep session alive
                    async with self.quota_service_factory() as quota_svc:
                        quota_available = await quota_svc.check_quota_available(
                            request.state.user_id, "api_call", 1, "daily"
                        )
                        if not quota_available:
                            return JSONResponse(
                                status_code=429,
                                content={
                                    "error": "API quota exceeded",
                                    "message": "You have exceeded your API quota. Please upgrade your plan."
                                }
                            )
            except Exception as e:
                logger.error(f"Quota check failed: {e}")

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(
            max(0, limit - self.rate_limiter.get_request_count(key, endpoint))
        )
        response.headers["X-RateLimit-Reset"] = str(
            int((datetime.now(timezone.utc) + timedelta(seconds=60)).timestamp())
        )

        return response

    def _get_rate_limit_params(self, request: Request) -> Tuple[str, str, int]:
        """
        Get rate limit parameters for the request.

        Args:
            request: Incoming request

        Returns:
            Tuple of (key, endpoint, limit)
        """
        # Get endpoint path
        endpoint = request.url.path

        # Determine key (user_id or IP)
        if hasattr(request.state, 'user_id') and request.state.user_id:
            key = f"user:{request.state.user_id}"
        else:
            # Use IP address for anonymous requests
            key = f"ip:{request.client.host if request.client else 'unknown'}"

        # Determine limit based on endpoint type
        if any(endpoint.startswith(path) for path in self.public_endpoints):
            # Public endpoints have lower limits
            limit = max(10, self.requests_per_minute // 6)
        else:
            limit = self.requests_per_minute

        return key, endpoint, limit

    async def reset_rate_limit(self, user_id: int, endpoint: str):
        """
        Reset rate limit for a user and endpoint.

        Args:
            user_id: User ID
            endpoint: API endpoint path
        """
        key = f"user:{user_id}"
        await self.rate_limiter.reset(key, endpoint)

    async def get_rate_limit_status(self, user_id: int, endpoint: str) -> dict:
        """
        Get current rate limit status for a user.

        Args:
            user_id: User ID
            endpoint: API endpoint path

        Returns:
            Dictionary with rate limit status
        """
        key = f"user:{user_id}"
        request_count = self.rate_limiter.get_request_count(key, endpoint)

        return {
            "endpoint": endpoint,
            "limit": self.requests_per_minute,
            "used": request_count,
            "remaining": max(0, self.requests_per_minute - request_count),
            "resets_at": datetime.now(timezone.utc) + timedelta(seconds=60)
        }
