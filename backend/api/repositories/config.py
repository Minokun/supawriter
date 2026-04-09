# -*- coding: utf-8 -*-
"""Configuration repository with user settings and preferences operations."""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, delete, func, desc
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from backend.api.db.models.config import (
    UserApiKey,
    UserModelConfig,
    UserPreferences,
    LLMProvider,
    UserServiceConfig
)
from backend.api.repositories.base import BaseRepository


class UserApiKeyRepository(BaseRepository[UserApiKey]):
    """
    Repository for UserApiKey model with API key operations.

    Extends BaseRepository with API key queries for third-party
    service integration and secure key management.
    """

    def __init__(self, session: AsyncSession):
        """Initialize UserApiKey repository."""
        super().__init__(session, UserApiKey)

    async def get_by_user_and_service(
        self,
        user_id: int,
        service_name: str
    ) -> Optional[UserApiKey]:
        """
        Get API key for a user and specific service.

        Args:
            user_id: User ID
            service_name: Service name (openai, anthropic, qiniu, etc.)

        Returns:
            UserApiKey instance or None if not found
        """
        stmt = (
            select(self.model)
            .where(
                and_(
                    self.model.user_id == user_id,
                    self.model.service_name == service_name,
                    self.model.is_active == True
                )
            )
        )

        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_all_user_keys(
        self,
        user_id: int,
        active_only: bool = True
    ) -> List[UserApiKey]:
        """
        Get all API keys for a user.

        Args:
            user_id: User ID
            active_only: Only return active keys

        Returns:
            List of UserApiKey instances
        """
        stmt = select(self.model).where(self.model.user_id == user_id)

        if active_only:
            stmt = stmt.where(self.model.is_active == True)

        stmt = stmt.order_by(desc(self.model.created_at))

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_service(
        self,
        service_name: str,
        active_only: bool = True
    ) -> List[UserApiKey]:
        """
        Get all API keys for a specific service.

        Args:
            service_name: Service name
            active_only: Only return active keys

        Returns:
            List of UserApiKey instances
        """
        stmt = select(self.model).where(self.model.service_name == service_name)

        if active_only:
            stmt = stmt.where(self.model.is_active == True)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create_or_update_key(
        self,
        user_id: int,
        service_name: str,
        encrypted_key: str
    ) -> UserApiKey:
        """
        Create or update API key for a user and service.

        Args:
            user_id: User ID
            service_name: Service name
            encrypted_key: Encrypted API key

        Returns:
            Created or updated UserApiKey instance
        """
        existing = await self.get_by_user_and_service(user_id, service_name)

        if existing:
            # Update existing key
            existing.encrypted_key = encrypted_key
            existing.is_active = True
            existing.updated_at = datetime.utcnow()
            return existing

        # Create new key
        api_key = UserApiKey(
            user_id=user_id,
            service_name=service_name,
            encrypted_key=encrypted_key,
            is_active=True
        )
        self.session.add(api_key)
        await self.session.flush()
        return api_key

    async def deactivate_key(
        self,
        user_id: int,
        service_name: str
    ) -> Optional[UserApiKey]:
        """
        Deactivate API key for a user and service.

        Args:
            user_id: User ID
            service_name: Service name

        Returns:
            Deactivated UserApiKey instance or None if not found
        """
        api_key = await self.get_by_user_and_service(user_id, service_name)
        if api_key:
            api_key.is_active = False
            return api_key
        return None

    async def delete_by_user(self, user_id: int) -> int:
        """
        Delete all API keys for a user.

        Args:
            user_id: User ID

        Returns:
            Number of keys deleted
        """
        stmt = delete(self.model).where(self.model.user_id == user_id)
        result = await self.session.execute(stmt)
        return result.rowcount


class UserModelConfigRepository(BaseRepository[UserModelConfig]):
    """
    Repository for UserModelConfig with AI model configuration operations.

    Extends BaseRepository with model config queries for different
    AI providers and use cases.
    """

    def __init__(self, session: AsyncSession):
        """Initialize UserModelConfig repository."""
        super().__init__(session, UserModelConfig)

    async def get_by_user_and_type(
        self,
        user_id: int,
        config_type: str
    ) -> Optional[UserModelConfig]:
        """
        Get model config for a user and config type.

        Args:
            user_id: User ID
            config_type: Config type (chat, writer, embedding, image)

        Returns:
            UserModelConfig instance or None if not found
        """
        stmt = (
            select(self.model)
            .where(
                and_(
                    self.model.user_id == user_id,
                    self.model.config_type == config_type
                )
            )
        )

        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_all_user_configs(
        self,
        user_id: int
    ) -> List[UserModelConfig]:
        """
        Get all model configs for a user.

        Args:
            user_id: User ID

        Returns:
            List of UserModelConfig instances
        """
        return await self.list(
            filters={"user_id": user_id},
            order_by="created_at DESC"
        )

    async def get_by_provider(
        self,
        user_id: int,
        provider: str
    ) -> List[UserModelConfig]:
        """
        Get all configs for a user by provider.

        Args:
            user_id: User ID
            provider: Provider name (openai, anthropic, etc.)

        Returns:
            List of UserModelConfig instances
        """
        return await self.list(
            filters={"user_id": user_id, "provider": provider},
            order_by="created_at DESC"
        )

    async def create_or_update_config(
        self,
        user_id: int,
        config_type: str,
        provider: str,
        model_name: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> UserModelConfig:
        """
        Create or update model config.

        Args:
            user_id: User ID
            config_type: Config type
            provider: Provider name
            model_name: Model name
            parameters: Optional model parameters

        Returns:
            Created or updated UserModelConfig instance
        """
        existing = await self.get_by_user_and_type(user_id, config_type)

        if existing:
            # Update existing config
            existing.provider = provider
            existing.model_name = model_name
            existing.parameters = parameters
            existing.updated_at = datetime.utcnow()
            return existing

        # Create new config
        config = UserModelConfig(
            user_id=user_id,
            config_type=config_type,
            provider=provider,
            model_name=model_name,
            parameters=parameters
        )
        self.session.add(config)
        await self.session.flush()
        return config

    async def update_parameters(
        self,
        config_id: int,
        parameters: Dict[str, Any]
    ) -> Optional[UserModelConfig]:
        """
        Update model configuration parameters.

        Args:
            config_id: Config ID
            parameters: New parameters

        Returns:
            Updated UserModelConfig instance or None
        """
        return await self.update(config_id, parameters=parameters)

    async def delete_by_user(self, user_id: int) -> int:
        """
        Delete all model configs for a user.

        Args:
            user_id: User ID

        Returns:
            Number of configs deleted
        """
        stmt = delete(self.model).where(self.model.user_id == user_id)
        result = await self.session.execute(stmt)
        return result.rowcount


class UserPreferencesRepository(BaseRepository[UserPreferences]):
    """
    Repository for UserPreferences with user settings operations.

    Extends BaseRepository with preference queries for user
    customization and UI settings.
    """

    def __init__(self, session: AsyncSession):
        """Initialize UserPreferences repository."""
        super().__init__(session, UserPreferences)

    async def get_user_preferences(
        self,
        user_id: int
    ) -> Optional[UserPreferences]:
        """
        Get preferences for a user.

        Args:
            user_id: User ID

        Returns:
            UserPreferences instance or None if not found
        """
        return await self.get_by_id(user_id)

    async def create_or_update_preferences(
        self,
        user_id: int,
        editor_theme: str = "light",
        editor_font_size: int = 14,
        notification_enabled: bool = True,
        wechat_preview_enabled: bool = True,
        additional_settings: Optional[Dict[str, Any]] = None
    ) -> UserPreferences:
        """
        Create or update user preferences.

        Args:
            user_id: User ID
            editor_theme: Editor theme
            editor_font_size: Editor font size
            notification_enabled: Enable notifications
            wechat_preview_enabled: Enable WeChat preview
            additional_settings: Additional settings as dict

        Returns:
            Created or updated UserPreferences instance
        """
        existing = await self.get_user_preferences(user_id)

        if existing:
            # Update existing preferences
            existing.editor_theme = editor_theme
            existing.editor_font_size = editor_font_size
            existing.notification_enabled = notification_enabled
            existing.wechat_preview_enabled = wechat_preview_enabled
            existing.additional_settings = additional_settings
            return existing

        # Create new preferences
        preferences = UserPreferences(
            user_id=user_id,
            editor_theme=editor_theme,
            editor_font_size=editor_font_size,
            notification_enabled=notification_enabled,
            wechat_preview_enabled=wechat_preview_enabled,
            additional_settings=additional_settings
        )
        self.session.add(preferences)
        await self.session.flush()
        return preferences

    async def update_editor_settings(
        self,
        user_id: int,
        theme: Optional[str] = None,
        font_size: Optional[int] = None
    ) -> Optional[UserPreferences]:
        """
        Update editor-specific settings.

        Args:
            user_id: User ID
            theme: Editor theme
            font_size: Font size

        Returns:
            Updated UserPreferences instance or None
        """
        preferences = await self.get_user_preferences(user_id)
        if not preferences:
            return None

        if theme is not None:
            preferences.editor_theme = theme
        if font_size is not None:
            preferences.editor_font_size = font_size

        return preferences

    async def update_notification_settings(
        self,
        user_id: int,
        notification_enabled: Optional[bool] = None,
        wechat_preview_enabled: Optional[bool] = None
    ) -> Optional[UserPreferences]:
        """
        Update notification settings.

        Args:
            user_id: User ID
            notification_enabled: Enable notifications
            wechat_preview_enabled: Enable WeChat preview

        Returns:
            Updated UserPreferences instance or None
        """
        preferences = await self.get_user_preferences(user_id)
        if not preferences:
            return None

        if notification_enabled is not None:
            preferences.notification_enabled = notification_enabled
        if wechat_preview_enabled is not None:
            preferences.wechat_preview_enabled = wechat_preview_enabled

        return preferences

    async def update_additional_settings(
        self,
        user_id: int,
        settings: Dict[str, Any]
    ) -> Optional[UserPreferences]:
        """
        Update additional settings.

        Args:
            user_id: User ID
            settings: Settings to merge/update

        Returns:
            Updated UserPreferences instance or None
        """
        preferences = await self.get_user_preferences(user_id)
        if not preferences:
            return None

        if preferences.additional_settings is None:
            preferences.additional_settings = {}
        preferences.additional_settings.update(settings)

        return preferences


class LLMProviderRepository(BaseRepository[LLMProvider]):
    """
    Repository for LLMProvider with LLM provider configuration operations.

    Extends BaseRepository with provider queries for custom
    LLM endpoints and configurations.
    """

    def __init__(self, session: AsyncSession):
        """Initialize LLMProvider repository."""
        super().__init__(session, LLMProvider)

    async def get_by_user_and_provider(
        self,
        user_id: int,
        provider_name: str
    ) -> Optional[LLMProvider]:
        """
        Get LLM provider config for a user.

        Args:
            user_id: User ID
            provider_name: Provider name

        Returns:
            LLMProvider instance or None if not found
        """
        stmt = (
            select(self.model)
            .where(
                and_(
                    self.model.user_id == user_id,
                    self.model.provider_name == provider_name
                )
            )
        )

        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_all_user_providers(
        self,
        user_id: int
    ) -> List[LLMProvider]:
        """
        Get all LLM provider configs for a user.

        Args:
            user_id: User ID

        Returns:
            List of LLMProvider instances
        """
        return await self.list(
            filters={"user_id": user_id},
            order_by="created_at DESC"
        )

    async def create_or_update_provider(
        self,
        user_id: int,
        provider_name: str,
        api_endpoint: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> LLMProvider:
        """
        Create or update LLM provider config.

        Args:
            user_id: User ID
            provider_name: Provider name
            api_endpoint: API endpoint URL
            config: Provider configuration

        Returns:
            Created or updated LLMProvider instance
        """
        existing = await self.get_by_user_and_provider(user_id, provider_name)

        if existing:
            # Update existing provider
            existing.api_endpoint = api_endpoint
            existing.config = config
            existing.updated_at = datetime.utcnow()
            return existing

        # Create new provider
        provider = LLMProvider(
            user_id=user_id,
            provider_name=provider_name,
            api_endpoint=api_endpoint,
            config=config
        )
        self.session.add(provider)
        await self.session.flush()
        return provider

    async def update_config(
        self,
        provider_id: int,
        config: Dict[str, Any]
    ) -> Optional[LLMProvider]:
        """
        Update provider configuration.

        Args:
            provider_id: Provider ID
            config: New configuration

        Returns:
            Updated LLMProvider instance or None
        """
        return await self.update(provider_id, config=config)

    async def delete_by_user(self, user_id: int) -> int:
        """
        Delete all LLM provider configs for a user.

        Args:
            user_id: User ID

        Returns:
            Number of providers deleted
        """
        stmt = delete(self.model).where(self.model.user_id == user_id)
        result = await self.session.execute(stmt)
        return result.rowcount


class UserServiceConfigRepository(BaseRepository[UserServiceConfig]):
    """
    Repository for UserServiceConfig with service configuration operations.

    Extends BaseRepository with service config queries for
    third-party service integrations.
    """

    def __init__(self, session: AsyncSession):
        """Initialize UserServiceConfig repository."""
        super().__init__(session, UserServiceConfig)

    async def get_by_user_and_service(
        self,
        user_id: int,
        service_name: str
    ) -> Optional[UserServiceConfig]:
        """
        Get service config for a user.

        Args:
            user_id: User ID
            service_name: Service name (qiniu, serper, etc.)

        Returns:
            UserServiceConfig instance or None if not found
        """
        stmt = (
            select(self.model)
            .where(
                and_(
                    self.model.user_id == user_id,
                    self.model.service_name == service_name
                )
            )
        )

        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_all_user_services(
        self,
        user_id: int
    ) -> List[UserServiceConfig]:
        """
        Get all service configs for a user.

        Args:
            user_id: User ID

        Returns:
            List of UserServiceConfig instances
        """
        return await self.list(
            filters={"user_id": user_id},
            order_by="created_at DESC"
        )

    async def create_or_update_service(
        self,
        user_id: int,
        service_name: str,
        config: Dict[str, Any]
    ) -> UserServiceConfig:
        """
        Create or update service config.

        Args:
            user_id: User ID
            service_name: Service name
            config: Service configuration

        Returns:
            Created or updated UserServiceConfig instance
        """
        existing = await self.get_by_user_and_service(user_id, service_name)

        if existing:
            # Update existing config
            existing.config = config
            existing.updated_at = datetime.utcnow()
            return existing

        # Create new config
        service_config = UserServiceConfig(
            user_id=user_id,
            service_name=service_name,
            config=config
        )
        self.session.add(service_config)
        await self.session.flush()
        return service_config

    async def update_config(
        self,
        config_id: int,
        config: Dict[str, Any]
    ) -> Optional[UserServiceConfig]:
        """
        Update service configuration.

        Args:
            config_id: Config ID
            config: New configuration

        Returns:
            Updated UserServiceConfig instance or None
        """
        return await self.update(config_id, config=config)

    async def delete_by_user(self, user_id: int) -> int:
        """
        Delete all service configs for a user.

        Args:
            user_id: User ID

        Returns:
            Number of configs deleted
        """
        stmt = delete(self.model).where(self.model.user_id == user_id)
        result = await self.session.execute(stmt)
        return result.rowcount
