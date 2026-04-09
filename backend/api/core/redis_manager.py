"""Redis client manager with connection pooling."""
import redis.asyncio as redis
from typing import Optional
import logging
from backend.api.core.config import get_settings

logger = logging.getLogger(__name__)


class RedisManager:
    """Redis connection manager with async support."""
    
    def __init__(self):
        """Initialize Redis manager."""
        self._client: Optional[redis.Redis] = None
        self._pool: Optional[redis.ConnectionPool] = None
    
    async def connect(self):
        """Create Redis connection pool."""
        if self._client is not None:
            return
        
        settings = get_settings()
        redis_config = settings.redis
        
        try:
            self._pool = redis.ConnectionPool.from_url(
                redis_config.get_url(),
                max_connections=redis_config.max_connections,
                socket_timeout=redis_config.socket_timeout,
                socket_connect_timeout=redis_config.socket_connect_timeout,
                retry_on_timeout=redis_config.retry_on_timeout,
                health_check_interval=redis_config.health_check_interval,
                decode_responses=False  # Keep binary for flexibility
            )
            
            self._client = redis.Redis(connection_pool=self._pool)
            
            # Test connection
            await self._client.ping()
            logger.info("✓ Redis connection established")
            
        except redis.RedisError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    async def disconnect(self):
        """Close Redis connection."""
        if self._client:
            await self._client.close()
            self._client = None
        
        if self._pool:
            await self._pool.disconnect()
            self._pool = None
        
        logger.info("✓ Redis connection closed")
    
    def get_client(self) -> redis.Redis:
        """Get Redis client instance."""
        if self._client is None:
            raise RuntimeError("Redis client not initialized. Call connect() first.")
        return self._client
    
    async def health_check(self) -> bool:
        """Check Redis health."""
        try:
            if self._client:
                await self._client.ping()
                return True
        except redis.RedisError:
            pass
        return False


# Global Redis manager instance
_redis_manager: Optional[RedisManager] = None


def get_redis_manager() -> RedisManager:
    """Get Redis manager instance (singleton)."""
    global _redis_manager
    if _redis_manager is None:
        _redis_manager = RedisManager()
    return _redis_manager


async def get_redis_client() -> redis.Redis:
    """Get Redis client for dependency injection."""
    manager = get_redis_manager()
    return manager.get_client()
