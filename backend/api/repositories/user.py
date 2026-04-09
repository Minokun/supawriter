"""User repository with authentication-specific operations."""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, update
from datetime import datetime, timezone
from typing import Optional, List
from backend.api.db.models.user import User, OAuthAccount
from backend.api.repositories.base import BaseRepository


class OAuthAccountRepository(BaseRepository[OAuthAccount]):
    """Repository for OAuth account operations."""

    def __init__(self, session: AsyncSession):
        """Initialize OAuthAccount repository."""
        super().__init__(session, OAuthAccount)

    async def get_by_provider(
        self,
        provider: str,
        provider_user_id: str
    ) -> Optional[OAuthAccount]:
        """
        Get OAuth account by provider and provider user ID.

        Args:
            provider: OAuth provider name (google, wechat, etc.)
            provider_user_id: User ID from the OAuth provider

        Returns:
            OAuthAccount instance or None
        """
        stmt = select(self.model).where(
            and_(
                self.model.provider == provider,
                self.model.provider_user_id == provider_user_id
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_user(self, user_id: int) -> List[OAuthAccount]:
        """
        List all OAuth accounts for a user.

        Args:
            user_id: User ID

        Returns:
            List of OAuthAccount instances
        """
        return await self.list(filters={"user_id": user_id})

    async def update_tokens(
        self,
        id: int,
        access_token: Optional[str] = None,
        refresh_token: Optional[str] = None,
        token_expires_at: Optional[datetime] = None
    ) -> Optional[OAuthAccount]:
        """
        Update OAuth tokens.

        Args:
            id: OAuth account ID
            access_token: New access token
            refresh_token: New refresh token
            token_expires_at: Token expiration timestamp

        Returns:
            Updated OAuthAccount instance or None
        """
        update_data = {}
        if access_token is not None:
            update_data['access_token'] = access_token
        if refresh_token is not None:
            update_data['refresh_token'] = refresh_token
        if token_expires_at is not None:
            update_data['token_expires_at'] = token_expires_at

        if not update_data:
            return None

        return await self.update(id, **update_data)


class UserRepository(BaseRepository[User]):
    """
    Repository for User model with authentication-specific operations.

    Extends BaseRepository with user-specific queries for authentication,
    profile management, and OAuth integration.
    """

    def __init__(self, session: AsyncSession):
        """Initialize User repository."""
        super().__init__(session, User)
        # Initialize OAuth account repository
        self.oauth_account_repo = OAuthAccountRepository(session)

    async def get_by_username(self, username: str) -> Optional[User]:
        """
        Get user by username.

        Args:
            username: Username to look up

        Returns:
            User instance or None if not found
        """
        return await self.get_by_field('username', username)

    async def get_by_email(self, email: str) -> Optional[User]:
        """
        Get user by email.

        Args:
            email: Email address to look up

        Returns:
            User instance or None if not found
        """
        return await self.get_by_field('email', email)

    async def username_exists(self, username: str) -> bool:
        """
        Check if username already exists.

        Args:
            username: Username to check

        Returns:
            True if username exists, False otherwise
        """
        stmt = select(self.model).where(self.model.username == username)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def email_exists(self, email: str) -> bool:
        """
        Check if email already exists.

        Args:
            email: Email address to check

        Returns:
            True if email exists, False otherwise
        """
        stmt = select(self.model).where(self.model.email == email)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def create_with_oauth(
        self,
        username: str,
        email: str,
        provider: str,
        provider_user_id: str,
        access_token: Optional[str] = None,
        refresh_token: Optional[str] = None,
        display_name: Optional[str] = None,
        avatar_url: Optional[str] = None
    ) -> User:
        """
        Create a new user with OAuth account.

        Args:
            username: Username
            email: Email address
            provider: OAuth provider name
            provider_user_id: User ID from OAuth provider
            access_token: OAuth access token
            refresh_token: OAuth refresh token
            display_name: Display name
            avatar_url: Avatar URL

        Returns:
            Created User instance
        """
        # Create user
        user = await self.create(
            username=username,
            email=email,
            display_name=display_name,
            avatar_url=avatar_url,
            password_hash=None  # OAuth users don't have password
        )

        # Create OAuth account
        await self.oauth_account_repo.create(
            user_id=user.id,
            provider=provider,
            provider_user_id=provider_user_id,
            access_token=access_token,
            refresh_token=refresh_token
        )

        return user

    async def get_by_oauth_provider(
        self,
        provider: str,
        provider_user_id: str
    ) -> Optional[User]:
        """
        Get user by OAuth provider and provider user ID.

        Args:
            provider: OAuth provider name
            provider_user_id: User ID from OAuth provider

        Returns:
            User instance or None if not found
        """
        # Find OAuth account
        oauth_account = await self.oauth_account_repo.get_by_provider(
            provider, provider_user_id
        )

        if oauth_account:
            # Return the user
            return await self.get_by_id(oauth_account.user_id)

        return None

    async def update_last_login(self, user_id: int) -> Optional[User]:
        """
        Update user's last login timestamp.

        Args:
            user_id: User ID

        Returns:
            Updated User instance or None if not found
        """
        return await self.update(user_id, last_login=datetime.now(timezone.utc))

    async def change_password(self, user_id: int, new_password_hash: str) -> Optional[User]:
        """
        Change user's password.

        Args:
            user_id: User ID
            new_password_hash: New password hash

        Returns:
            Updated User instance or None if not found
        """
        return await self.update(user_id, password_hash=new_password_hash)

    async def deactivate_by_email(self, email: str) -> Optional[User]:
        """
        Deactivate user by email (sets password_hash to None).

        Args:
            email: Email address

        Returns:
            Updated User instance or None if not found
        """
        user = await self.get_by_email(email)
        if user:
            return await self.update(user.id, password_hash=None)
        return None

    async def update_profile(
        self,
        user_id: int,
        display_name: Optional[str] = None,
        avatar_url: Optional[str] = None,
        motto: Optional[str] = None
    ) -> Optional[User]:
        """
        Update user's profile information.

        Args:
            user_id: User ID
            display_name: Display name
            avatar_url: Avatar URL
            motto: User motto/bio

        Returns:
            Updated User instance or None if not found
        """
        update_data = {}
        if display_name is not None:
            update_data['display_name'] = display_name
        if avatar_url is not None:
            update_data['avatar_url'] = avatar_url
        if motto is not None:
            update_data['motto'] = motto

        if not update_data:
            return await self.get_by_id(user_id)

        return await self.update(user_id, **update_data)

    async def get_user_with_oauth_accounts(self, user_id: int) -> Optional[User]:
        """
        Get user with their OAuth accounts pre-loaded.

        Args:
            user_id: User ID

        Returns:
            User instance with oauth_accounts relationship loaded, or None
        """
        from sqlalchemy.orm import selectinload
        stmt = select(self.model).where(
            self.model.id == user_id
        ).options(selectinload(self.model.oauth_accounts))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def search_by_username_or_email(
        self,
        query: str,
        limit: int = 10
    ) -> List[User]:
        """
        Search users by username or email (partial match).

        Args:
            query: Search query
            limit: Maximum results to return

        Returns:
            List of matching User instances
        """
        search_pattern = f"%{query}%"
        stmt = select(self.model).where(
            or_(
                self.model.username.ilike(search_pattern),
                self.model.email.ilike(search_pattern)
            )
        ).limit(limit)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())
