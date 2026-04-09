"""Performance monitoring and metrics collection."""
from typing import Optional, Callable
from functools import wraps
import time
import logging
from contextlib import asynccontextmanager
from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry
from backend.api.core.config import get_settings

logger = logging.getLogger(__name__)

# Create a custom registry for better control
registry = CollectorRegistry()

# Request metrics
request_count = Counter(
    'api_requests_total',
    'Total API requests',
    ['method', 'endpoint', 'status'],
    registry=registry
)

request_duration = Histogram(
    'api_request_duration_seconds',
    'API request duration in seconds',
    ['method', 'endpoint'],
    registry=registry
)

# Database metrics
db_query_count = Counter(
    'db_queries_total',
    'Total database queries',
    ['operation', 'table'],
    registry=registry
)

db_query_duration = Histogram(
    'db_query_duration_seconds',
    'Database query duration in seconds',
    ['operation', 'table'],
    registry=registry
)

slow_query_count = Counter(
    'db_slow_queries_total',
    'Total slow database queries',
    ['operation', 'table'],
    registry=registry
)

# Connection pool metrics
db_pool_size = Gauge(
    'db_pool_size',
    'Database connection pool size',
    registry=registry
)

db_pool_checked_in = Gauge(
    'db_pool_checked_in',
    'Database connections checked in',
    registry=registry
)

db_pool_overflow = Gauge(
    'db_pool_overflow',
    'Database connection pool overflow',
    registry=registry
)

# Cache metrics
cache_hits = Counter(
    'cache_hits_total',
    'Total cache hits',
    ['cache_type'],
    registry=registry
)

cache_misses = Counter(
    'cache_misses_total',
    'Total cache misses',
    ['cache_type'],
    registry=registry
)

# Rate limit metrics
rate_limit_exceeded = Counter(
    'rate_limit_exceeded_total',
    'Total rate limit exceeded events',
    ['endpoint'],
    registry=registry
)

# Quota metrics
quota_exceeded = Counter(
    'quota_exceeded_total',
    'Total quota exceeded events',
    ['quota_type'],
    registry=registry
)

quota_usage = Gauge(
    'quota_usage',
    'Current quota usage',
    ['user_id', 'quota_type'],
    registry=registry
)


class MetricsCollector:
    """Metrics collector for application monitoring."""
    
    def __init__(self):
        """Initialize metrics collector."""
        self.settings = get_settings()
    
    def record_request(self, method: str, endpoint: str, status: int, duration: float):
        """Record API request metrics."""
        if not self.settings.monitoring.enabled:
            return
        
        request_count.labels(method=method, endpoint=endpoint, status=status).inc()
        request_duration.labels(method=method, endpoint=endpoint).observe(duration)
    
    def record_db_query(self, operation: str, table: str, duration: float):
        """Record database query metrics."""
        if not self.settings.monitoring.enabled:
            return
        
        db_query_count.labels(operation=operation, table=table).inc()
        db_query_duration.labels(operation=operation, table=table).observe(duration)
        
        # Check for slow queries
        if duration > self.settings.monitoring.slow_query_threshold:
            slow_query_count.labels(operation=operation, table=table).inc()
            logger.warning(
                f"Slow query detected: {operation} on {table} took {duration:.2f}s"
            )
    
    def update_pool_metrics(self, size: int, checked_in: int, overflow: int):
        """Update connection pool metrics."""
        if not self.settings.monitoring.enabled:
            return
        
        db_pool_size.set(size)
        db_pool_checked_in.set(checked_in)
        db_pool_overflow.set(overflow)
    
    def record_cache_hit(self, cache_type: str):
        """Record cache hit."""
        if not self.settings.monitoring.enabled:
            return
        
        cache_hits.labels(cache_type=cache_type).inc()
    
    def record_cache_miss(self, cache_type: str):
        """Record cache miss."""
        if not self.settings.monitoring.enabled:
            return
        
        cache_misses.labels(cache_type=cache_type).inc()
    
    def record_rate_limit_exceeded(self, endpoint: str):
        """Record rate limit exceeded event."""
        if not self.settings.monitoring.enabled:
            return
        
        rate_limit_exceeded.labels(endpoint=endpoint).inc()
    
    def record_quota_exceeded(self, quota_type: str):
        """Record quota exceeded event."""
        if not self.settings.monitoring.enabled:
            return
        
        quota_exceeded.labels(quota_type=quota_type).inc()
    
    def update_quota_usage(self, user_id: int, quota_type: str, usage: float):
        """Update quota usage gauge."""
        if not self.settings.monitoring.enabled:
            return
        
        quota_usage.labels(user_id=str(user_id), quota_type=quota_type).set(usage)


# Global metrics collector instance
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Get metrics collector instance (singleton)."""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


def monitor_request(func: Callable):
    """Decorator to monitor API request performance."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        status = 200
        
        try:
            result = await func(*args, **kwargs)
            return result
        except Exception as e:
            status = 500
            raise
        finally:
            duration = time.time() - start_time
            
            # Extract method and endpoint from request
            # This is a simplified version - actual implementation would extract from FastAPI request
            method = "GET"
            endpoint = func.__name__
            
            collector = get_metrics_collector()
            collector.record_request(method, endpoint, status, duration)
    
    return wrapper


@asynccontextmanager
async def monitor_db_query(operation: str, table: str):
    """Context manager to monitor database query performance."""
    start_time = time.time()
    
    try:
        yield
    finally:
        duration = time.time() - start_time
        collector = get_metrics_collector()
        collector.record_db_query(operation, table, duration)


class QueryMonitor:
    """Monitor for database queries."""
    
    def __init__(self):
        """Initialize query monitor."""
        self.collector = get_metrics_collector()
    
    async def __aenter__(self):
        """Start monitoring."""
        self.start_time = time.time()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Stop monitoring and record metrics."""
        duration = time.time() - self.start_time
        
        # Record metrics
        if hasattr(self, 'operation') and hasattr(self, 'table'):
            self.collector.record_db_query(self.operation, self.table, duration)
    
    def set_operation(self, operation: str, table: str):
        """Set operation details."""
        self.operation = operation
        self.table = table
        return self


def get_registry():
    """Get Prometheus registry for metrics export."""
    return registry
