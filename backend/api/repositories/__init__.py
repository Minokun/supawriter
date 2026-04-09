"""Repository pattern implementation for data access layer."""
from backend.api.repositories.base import BaseRepository
from backend.api.repositories.user import UserRepository, OAuthAccountRepository
from backend.api.repositories.article import ArticleRepository
from backend.api.repositories.quota import QuotaRepository, QuotaUsageRepository
from backend.api.repositories.audit import AuditLogRepository
from backend.api.repositories.chat import ChatSessionRepository, ChatMessageRepository
from backend.api.repositories.config import (
    UserApiKeyRepository,
    UserModelConfigRepository,
    UserPreferencesRepository,
    LLMProviderRepository,
    UserServiceConfigRepository
)
from backend.api.repositories.payment import (
    SubscriptionRepository,
    OrderRepository,
    QuotaPackRepository
)
from backend.api.repositories.hotspot import (
    HotspotSourceRepository,
    HotspotItemRepository,
    HotspotRankHistoryRepository
)

__all__ = [
    'BaseRepository',
    'UserRepository',
    'OAuthAccountRepository',
    'ArticleRepository',
    'QuotaRepository',
    'QuotaUsageRepository',
    'AuditLogRepository',
    'ChatSessionRepository',
    'ChatMessageRepository',
    'UserApiKeyRepository',
    'UserModelConfigRepository',
    'UserPreferencesRepository',
    'LLMProviderRepository',
    'UserServiceConfigRepository',
    'SubscriptionRepository',
    'OrderRepository',
    'QuotaPackRepository',
    'HotspotSourceRepository',
    'HotspotItemRepository',
    'HotspotRankHistoryRepository',
]
