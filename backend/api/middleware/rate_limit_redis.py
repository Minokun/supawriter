"""Redis-based rate limiter for production use."""
from typing import Tuple, Optional
from datetime import datetime, timezone
import redis.asyncio as redis
import logging

logger = logging.getLogger(__name__)


class RateLimiterRedis:
    """
    Redis-based rate limiter using sorted sets (ZSET) for sliding window.
    
    This implementation is production-ready and supports distributed deployments.
    """

    def __init__(self, redis_client: redis.Redis, key_prefix: str = "rate_limit"):
        """
        Initialize Redis rate limiter.

        Args:
            redis_client: Async Redis client instance
            key_prefix: Prefix for Redis keys
        """
        self.redis = redis_client
        self.key_prefix = key_prefix

    def _make_key(self, key: str, endpoint: str) -> str:
        """Generate Redis key for rate limiting."""
        return f"{self.key_prefix}:{key}:{endpoint}"

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
        redis_key = self._make_key(key, endpoint)
        now = datetime.now(timezone.utc).timestamp()
        cutoff = now - window

        try:
            # Remove old requests outside the window
            await self.redis.zremrangebyscore(redis_key, 0, cutoff)

            # Count requests in current window
            count = await self.redis.zcard(redis_key)

            # Check if under limit (allow up to and including the limit)
            allowed = count < limit

            # Calculate retry_after if not allowed
            retry_after = 0
            if not allowed:
                # Get the oldest request timestamp
                oldest = await self.redis.zrange(redis_key, 0, 0, withscores=True)
                if oldest:
                    oldest_timestamp = oldest[0][1]
                    retry_after = int(window - (now - oldest_timestamp))
                    retry_after = max(1, retry_after)

            return allowed, retry_after

        except redis.RedisError as e:
            logger.error(f"Redis error in rate limiter: {e}")
            # Fail open - allow request if Redis is down
            return True, 0

    async def record_request(
        self,
        key: str,
        endpoint: str,
        timestamp: Optional[float] = None
    ):
        """
        Record a request for rate limiting.

        Args:
            key: Unique key (user_id or IP address)
            endpoint: API endpoint path
            timestamp: Request timestamp (defaults to now)
        """
        if timestamp is None:
            timestamp = datetime.now(timezone.utc).timestamp()

        redis_key = self._make_key(key, endpoint)

        try:
            # Add request to sorted set with timestamp as score
            await self.redis.zadd(redis_key, {str(timestamp): timestamp})
            
            # Set expiration to window + buffer
            await self.redis.expire(redis_key, 3600)  # 1 hour TTL

        except redis.RedisError as e:
            logger.error(f"Redis error recording request: {e}")

    async def reset(self, key: str, endpoint: str):
        """
        Reset rate limit for a key and endpoint.

        Args:
            key: Unique key (user_id or IP address)
            endpoint: API endpoint path
        """
        redis_key = self._make_key(key, endpoint)
        
        try:
            await self.redis.delete(redis_key)
        except redis.RedisError as e:
            logger.error(f"Redis error resetting rate limit: {e}")

    async def get_request_count(self, key: str, endpoint: str) -> int:
        """
        Get current request count for a key and endpoint.

        Args:
            key: Unique key (user_id or IP address)
            endpoint: API endpoint path

        Returns:
            Number of requests in the current window
        """
        redis_key = self._make_key(key, endpoint)
        
        try:
            return await self.redis.zcard(redis_key)
        except redis.RedisError as e:
            logger.error(f"Redis error getting request count: {e}")
            return 0

    async def get_all_limits(self, key: str) -> dict:
        """
        Get rate limit status for all endpoints for a key.

        Args:
            key: Unique key (user_id or IP address)

        Returns:
            Dictionary mapping endpoints to request counts
        """
        pattern = f"{self.key_prefix}:{key}:*"
        limits = {}
        
        try:
            async for redis_key in self.redis.scan_iter(match=pattern):
                # Extract endpoint from key
                endpoint = redis_key.decode().split(':', 2)[2]
                count = await self.redis.zcard(redis_key)
                limits[endpoint] = count
        except redis.RedisError as e:
            logger.error(f"Redis error getting all limits: {e}")
        
        return limits

    async def cleanup_expired(self, window: int = 3600):
        """
        Clean up expired rate limit entries.

        Args:
            window: Time window in seconds
        """
        pattern = f"{self.key_prefix}:*"
        now = datetime.now(timezone.utc).timestamp()
        cutoff = now - window
        
        try:
            async for redis_key in self.redis.scan_iter(match=pattern):
                await self.redis.zremrangebyscore(redis_key, 0, cutoff)
        except redis.RedisError as e:
            logger.error(f"Redis error cleaning up: {e}")
