"""Cache utilities with Redis backend."""
import json
import pickle
from typing import Optional, Any, Callable
from functools import wraps
import hashlib
import logging
from backend.api.core.redis_manager import get_redis_client
from backend.api.core.config import get_settings

logger = logging.getLogger(__name__)


def _make_cache_key(prefix: str, *args, **kwargs) -> str:
    """Generate cache key from function arguments."""
    # Create a string representation of args and kwargs
    key_parts = [prefix]
    
    # Add positional arguments
    for arg in args:
        if isinstance(arg, (str, int, float, bool)):
            key_parts.append(str(arg))
        else:
            # Hash complex objects
            key_parts.append(hashlib.md5(str(arg).encode()).hexdigest()[:8])
    
    # Add keyword arguments (sorted for consistency)
    for k, v in sorted(kwargs.items()):
        if isinstance(v, (str, int, float, bool)):
            key_parts.append(f"{k}={v}")
        else:
            key_parts.append(f"{k}={hashlib.md5(str(v).encode()).hexdigest()[:8]}")
    
    return ":".join(key_parts)


def cache(
    ttl: Optional[int] = None,
    key_prefix: Optional[str] = None,
    serializer: str = "json"
):
    """
    Cache decorator for async functions.
    
    Args:
        ttl: Time to live in seconds (None = use default from config)
        key_prefix: Custom key prefix (None = use function name)
        serializer: Serialization method ('json' or 'pickle')
    
    Example:
        @cache(ttl=300)
        async def get_user(user_id: int):
            return await user_repo.get_by_id(user_id)
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            settings = get_settings()
            
            # Skip cache if disabled
            if not settings.cache.enabled:
                return await func(*args, **kwargs)
            
            # Generate cache key
            prefix = key_prefix or f"cache:{func.__module__}.{func.__name__}"
            cache_key = _make_cache_key(prefix, *args, **kwargs)
            
            try:
                redis_client = await get_redis_client()
                
                # Try to get from cache
                cached = await redis_client.get(cache_key)
                if cached:
                    # Deserialize
                    if serializer == "json":
                        return json.loads(cached)
                    else:
                        return pickle.loads(cached)
                
                # Call function
                result = await func(*args, **kwargs)
                
                # Cache result
                cache_ttl = ttl or settings.cache.default_ttl
                if serializer == "json":
                    await redis_client.setex(
                        cache_key,
                        cache_ttl,
                        json.dumps(result, default=str)
                    )
                else:
                    await redis_client.setex(
                        cache_key,
                        cache_ttl,
                        pickle.dumps(result)
                    )
                
                return result
                
            except Exception as e:
                logger.warning(f"Cache error: {e}, falling back to function call")
                return await func(*args, **kwargs)
        
        return wrapper
    return decorator


async def invalidate_cache(pattern: str):
    """
    Invalidate cache entries matching pattern.
    
    Args:
        pattern: Redis key pattern (e.g., "cache:user:*")
    """
    try:
        redis_client = await get_redis_client()
        
        # Find matching keys
        keys = []
        async for key in redis_client.scan_iter(match=pattern):
            keys.append(key)
        
        # Delete keys
        if keys:
            await redis_client.delete(*keys)
            logger.info(f"Invalidated {len(keys)} cache entries matching '{pattern}'")
    
    except Exception as e:
        logger.error(f"Error invalidating cache: {e}")


async def get_cached(key: str, default: Any = None) -> Any:
    """
    Get value from cache.
    
    Args:
        key: Cache key
        default: Default value if not found
    
    Returns:
        Cached value or default
    """
    try:
        redis_client = await get_redis_client()
        value = await redis_client.get(key)
        
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return pickle.loads(value)
        
        return default
    
    except Exception as e:
        logger.error(f"Error getting cached value: {e}")
        return default


async def set_cached(key: str, value: Any, ttl: Optional[int] = None):
    """
    Set value in cache.
    
    Args:
        key: Cache key
        value: Value to cache
        ttl: Time to live in seconds
    """
    try:
        redis_client = await get_redis_client()
        settings = get_settings()
        
        cache_ttl = ttl or settings.cache.default_ttl
        
        # Try JSON first, fall back to pickle
        try:
            serialized = json.dumps(value, default=str)
        except (TypeError, ValueError):
            serialized = pickle.dumps(value)
        
        await redis_client.setex(key, cache_ttl, serialized)
    
    except Exception as e:
        logger.error(f"Error setting cached value: {e}")


async def delete_cached(key: str):
    """
    Delete value from cache.
    
    Args:
        key: Cache key
    """
    try:
        redis_client = await get_redis_client()
        await redis_client.delete(key)
    
    except Exception as e:
        logger.error(f"Error deleting cached value: {e}")


class CacheManager:
    """Cache manager for common operations."""
    
    def __init__(self):
        """Initialize cache manager."""
        self.settings = get_settings()
    
    async def get_user(self, user_id: int) -> Optional[dict]:
        """Get user from cache."""
        key = f"cache:user:{user_id}"
        return await get_cached(key)
    
    async def set_user(self, user_id: int, user_data: dict):
        """Set user in cache."""
        key = f"cache:user:{user_id}"
        await set_cached(key, user_data, self.settings.cache.user_ttl)
    
    async def invalidate_user(self, user_id: int):
        """Invalidate user cache."""
        key = f"cache:user:{user_id}"
        await delete_cached(key)
    
    async def get_quota(self, user_id: int, quota_type: str) -> Optional[dict]:
        """Get quota from cache."""
        key = f"cache:quota:{user_id}:{quota_type}"
        return await get_cached(key)
    
    async def set_quota(self, user_id: int, quota_type: str, quota_data: dict):
        """Set quota in cache."""
        key = f"cache:quota:{user_id}:{quota_type}"
        await set_cached(key, quota_data, self.settings.cache.quota_ttl)
    
    async def invalidate_quota(self, user_id: int, quota_type: Optional[str] = None):
        """Invalidate quota cache."""
        if quota_type:
            key = f"cache:quota:{user_id}:{quota_type}"
            await delete_cached(key)
        else:
            pattern = f"cache:quota:{user_id}:*"
            await invalidate_cache(pattern)
    
    async def get_article_list(self, user_id: int, filters: str) -> Optional[list]:
        """Get article list from cache."""
        key = f"cache:articles:{user_id}:{filters}"
        return await get_cached(key)
    
    async def set_article_list(self, user_id: int, filters: str, articles: list):
        """Set article list in cache."""
        key = f"cache:articles:{user_id}:{filters}"
        await set_cached(key, articles, self.settings.cache.article_list_ttl)
    
    async def invalidate_article_list(self, user_id: int):
        """Invalidate article list cache."""
        pattern = f"cache:articles:{user_id}:*"
        await invalidate_cache(pattern)


# Global cache manager instance
_cache_manager: Optional[CacheManager] = None


def get_cache_manager() -> CacheManager:
    """Get cache manager instance (singleton)."""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager
