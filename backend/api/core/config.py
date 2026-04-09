"""Application configuration using Pydantic Settings."""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
import os


class DatabaseConfig(BaseSettings):
    """Database configuration."""
    
    # Database connection
    host: str = "localhost"
    port: int = 5432
    database: str = "supawriter"
    user: str = "supawriter"
    password: str = ""
    url: Optional[str] = None
    
    # Connection pool
    pool_size: int = 5
    max_overflow: int = 10
    pool_timeout: int = 30
    pool_recycle: int = 3600
    pool_pre_ping: bool = True
    
    # Query settings
    echo: bool = False
    echo_pool: bool = False
    
    model_config = SettingsConfigDict(env_prefix="POSTGRES_")
    
    def get_url(self) -> str:
        """Get database URL."""
        if self.url:
            return self.url
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"
    
    def get_async_url(self) -> str:
        """Get async database URL."""
        return self.get_url().replace('postgresql://', 'postgresql+asyncpg://')


class RedisConfig(BaseSettings):
    """Redis configuration."""
    
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None
    url: Optional[str] = None
    
    # Connection pool
    max_connections: int = 10
    socket_timeout: int = 5
    socket_connect_timeout: int = 5
    
    # Retry settings
    retry_on_timeout: bool = True
    health_check_interval: int = 30
    
    model_config = SettingsConfigDict(env_prefix="REDIS_")
    
    def get_url(self) -> str:
        """Get Redis URL."""
        if self.url:
            return self.url
        
        if self.password:
            return f"redis://:{self.password}@{self.host}:{self.port}/{self.db}"
        return f"redis://{self.host}:{self.port}/{self.db}"


class RateLimitConfig(BaseSettings):
    """Rate limiting configuration."""
    
    enabled: bool = True
    requests_per_minute: int = 60
    use_redis: bool = True
    
    # Public endpoints (lower limits)
    public_requests_per_minute: int = 10
    
    # Exclude paths
    exclude_paths: list[str] = ["/health", "/metrics", "/docs", "/openapi.json"]
    
    model_config = SettingsConfigDict(env_prefix="RATE_LIMIT_")


class QuotaConfig(BaseSettings):
    """Quota configuration."""
    
    enabled: bool = True
    
    # Default quotas
    default_article_daily_limit: int = 10
    default_article_monthly_limit: int = 100
    default_api_daily_limit: int = 1000
    default_api_monthly_limit: int = 10000
    default_storage_limit_mb: int = 1000
    
    model_config = SettingsConfigDict(env_prefix="QUOTA_")


class AuditConfig(BaseSettings):
    """Audit logging configuration."""
    
    enabled: bool = True
    log_request_body: bool = True
    log_response_body: bool = False
    log_headers: bool = True
    
    # Sensitive fields to filter
    sensitive_fields: list[str] = [
        "password", "token", "api_key", "secret", 
        "authorization", "cookie", "session"
    ]
    
    model_config = SettingsConfigDict(env_prefix="AUDIT_")


class CacheConfig(BaseSettings):
    """Cache configuration."""
    
    enabled: bool = True
    default_ttl: int = 300  # 5 minutes
    
    # Cache TTLs for different data types
    user_ttl: int = 600  # 10 minutes
    quota_ttl: int = 60   # 1 minute
    article_list_ttl: int = 300  # 5 minutes
    
    model_config = SettingsConfigDict(env_prefix="CACHE_")


class MonitoringConfig(BaseSettings):
    """Monitoring and metrics configuration."""
    
    enabled: bool = True
    prometheus_enabled: bool = True
    
    # Slow query threshold (seconds)
    slow_query_threshold: float = 1.0
    
    # Health check intervals
    health_check_interval: int = 30
    
    model_config = SettingsConfigDict(env_prefix="MONITORING_")


class AppConfig(BaseSettings):
    """Main application configuration."""
    
    # Application
    app_name: str = "SupaWriter API"
    app_version: str = "2.0.0"
    debug: bool = False
    environment: str = "development"
    
    # API
    api_prefix: str = "/api"
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
    ]
    
    # Security
    secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 60 * 24 * 7  # 7 days
    
    # Sub-configurations
    database: DatabaseConfig = DatabaseConfig()
    redis: RedisConfig = RedisConfig()
    rate_limit: RateLimitConfig = RateLimitConfig()
    quota: QuotaConfig = QuotaConfig()
    audit: AuditConfig = AuditConfig()
    cache: CacheConfig = CacheConfig()
    monitoring: MonitoringConfig = MonitoringConfig()
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="ignore"  # 忽略额外的环境变量
    )


# Global settings instance
_settings: Optional[AppConfig] = None


def get_settings() -> AppConfig:
    """Get application settings (singleton)."""
    global _settings
    if _settings is None:
        _settings = AppConfig()
    return _settings


def reload_settings():
    """Reload settings from environment."""
    global _settings
    _settings = None
    return get_settings()
