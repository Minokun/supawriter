"""User service with authentication and profile management."""
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Dict
from datetime import datetime, timezone
import passlib.hash as hashlib
from backend.api.db.models.user import User
from backend.api.repositories.user import UserRepository, OAuthAccountRepository


class UserService:
    """
    Service layer for user operations.

    Handles business logic for user registration, authentication,
    password management, OAuth integration, and profile updates.
    """

    def __init__(self, session: AsyncSession, user_repository: UserRepository, oauth_repository: OAuthAccountRepository = None):
        """
        Initialize UserService.

        Args:
            session: Database session
            user_repository: User repository instance
            oauth_repository: OAuth account repository instance (optional)
        """
        self.session = session
        self.user_repo = user_repository
        self.oauth_repo = oauth_repository or OAuthAccountRepository(session)

    async def register_user(
        self,
        username: str,
        email: str,
        password: str,
        display_name: Optional[str] = None,
        avatar_url: Optional[str] = None
    ) -> Optional[User]:
        """
        Register a new user.

        Args:
            username: Username (must be unique)
            email: Email address (must be unique)
            password: Plain text password (will be hashed)
            display_name: Optional display name
            avatar_url: Optional avatar URL

        Returns:
            Created User instance or None if username/email already exists
        """
        # Check if username already exists
        if await self.user_repo.username_exists(username):
            return None

        # Check if email already exists
        if await self.user_repo.email_exists(email):
            return None

        # Hash password
        password_hash = self._hash_password(password)

        # Create user
        user = await self.user_repo.create(
            username=username,
            email=email,
            password_hash=password_hash,
            display_name=display_name or username,
            avatar_url=avatar_url,
            motto="创作改变世界"
        )

        return user

    async def authenticate_user(
        self,
        password: str,
        username: str = None,
        email: str = None
    ) -> Optional[User]:
        """
        Authenticate a user with username/email and password.

        Args:
            password: Plain text password
            username: Username (optional, used if email not provided)
            email: Email address (optional, preferred over username)

        Returns:
            Authenticated User instance or None if authentication fails
        """
        # Get user by email or username
        user = None
        if email:
            user = await self.user_repo.get_by_email(email)
        if not user and username:
            user = await self.user_repo.get_by_username(username)

        if not user or not user.password_hash:
            return None

        # Verify password
        if not self._verify_password(password, user.password_hash):
            return None

        # Update last login
        await self.user_repo.update_last_login(user.id)

        return user

    async def update_password(
        self,
        user_id: int,
        old_password: str,
        new_password: str
    ) -> bool:
        """
        Update user's password.

        Args:
            user_id: User ID
            old_password: Current password (for verification)
            new_password: New password to set

        Returns:
            True if password updated, False if old password doesn't match
        """
        # Get user
        user = await self.user_repo.get_by_id(user_id)
        if not user or not user.password_hash:
            return False

        # Verify old password
        if not self._verify_password(old_password, user.password_hash):
            return False

        # Hash new password
        new_password_hash = self._hash_password(new_password)

        # Update password
        await self.user_repo.change_password(user_id, new_password_hash)

        return True

    async def oauth_login(
        self,
        provider: str,
        provider_user_id: str,
        email: str,
        username: Optional[str] = None,
        avatar_url: Optional[str] = None
    ) -> User:
        """
        Handle OAuth login/registration.

        Args:
            provider: OAuth provider name (google, github, etc.)
            provider_user_id: User ID from the OAuth provider
            email: Email address from OAuth
            username: Optional username (generated from email if not provided)
            avatar_url: Optional avatar URL from OAuth

        Returns:
            User instance (existing or newly created)
        """
        # Try to find existing user by OAuth
        existing_user = await self.user_repo.get_by_oauth_provider(provider, provider_user_id)

        if existing_user:
            # Update last login and return
            await self.user_repo.update_last_login(existing_user.id)
            return existing_user

        # Create new user with OAuth
        generated_username = username or self._generate_username_from_email(email)

        user = await self.user_repo.create_with_oauth(
            username=generated_username,
            email=email,
            provider=provider,
            provider_user_id=provider_user_id,
            access_token=None,  # Will be set separately
            refresh_token=None,
            display_name=username or generated_username,
            avatar_url=avatar_url
        )

        return user

    async def get_user_profile(self, user_id: int) -> Optional[Dict]:
        """
        Get user profile information.

        Args:
            user_id: User ID

        Returns:
            Dictionary with user profile data or None if not found
        """
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            return None

        return {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "display_name": user.display_name,
            "avatar_url": user.avatar_url,
            "motto": user.motto,
            "created_at": user.created_at,
            "last_login": user.last_login,
            "is_superuser": user.is_superuser,
            "membership_tier": user.membership_tier
        }

    async def update_profile(
        self,
        user_id: int,
        display_name: Optional[str] = None,
        motto: Optional[str] = None,
        avatar_url: Optional[str] = None
    ) -> Optional[User]:
        """
        Update user profile.

        Args:
            user_id: User ID
            display_name: New display name
            motto: New motto
            avatar_url: New avatar URL

        Returns:
            Updated User instance or None if not found
        """
        return await self.user_repo.update_profile(
            user_id=user_id,
            display_name=display_name,
            motto=motto,
            avatar_url=avatar_url
        )

    async def get_profile_with_oauth(self, user_id: int) -> Optional[Dict]:
        """
        Get user profile with OAuth accounts.

        Args:
            user_id: User ID

        Returns:
            Dictionary with user profile data including OAuth accounts, or None
        """
        user = await self.user_repo.get_user_with_oauth_accounts(user_id)
        if not user:
            return None

        oauth_accounts = []
        for oa in user.oauth_accounts:
            oauth_accounts.append({
                "provider": oa.provider,
                "provider_user_id": oa.provider_user_id,
                "created_at": oa.created_at.isoformat() if oa.created_at else "",
            })

        return {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "display_name": user.display_name,
            "avatar_url": user.avatar_url,
            "motto": user.motto,
            "phone": user.phone,
            "phone_verified": user.phone_verified,
            "email_verified": user.email_verified,
            "has_password": user.password_hash is not None,
            "oauth_accounts": oauth_accounts,
            "created_at": user.created_at,
            "last_login": user.last_login,
        }

    async def bind_email(
        self,
        user_id: int,
        email: str,
        password: str
    ) -> Dict:
        """
        Bind email and password to an existing user (e.g. OAuth user).

        Args:
            user_id: User ID
            email: Email address to bind
            password: Password to set

        Returns:
            Dict with result info

        Raises:
            ValueError: If user already has password or email is taken
        """
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise ValueError("User not found")

        if user.password_hash:
            raise ValueError("User already has a password set")

        # Check if the email is already used by another user
        existing = await self.user_repo.get_by_email(email)
        if existing and existing.id != user_id:
            raise ValueError("Email already in use by another account")

        # Hash password and update user
        password_hash = self._hash_password(password)
        update_data = {"password_hash": password_hash}

        # If user has no email yet (unlikely but possible), set it
        if not user.email or user.email != email:
            # Only update email if it's different and not taken
            if not existing or existing.id == user_id:
                update_data["email"] = email

        await self.user_repo.update(user_id, **update_data)

        return {"message": "Email and password bound successfully"}

    async def unbind_oauth(self, user_id: int, provider: str) -> Dict:
        """
        Unbind an OAuth account from the user.

        Must keep at least one login method (password or another OAuth).

        Args:
            user_id: User ID
            provider: OAuth provider to unbind (e.g. 'google')

        Returns:
            Dict with result info

        Raises:
            ValueError: If unbinding would leave user with no login method
        """
        user = await self.user_repo.get_user_with_oauth_accounts(user_id)
        if not user:
            raise ValueError("User not found")

        # Find the OAuth account to unbind
        target_oauth = None
        for oa in user.oauth_accounts:
            if oa.provider == provider:
                target_oauth = oa
                break

        if target_oauth is None:
            raise ValueError(f"No {provider} account linked")

        # Check: must keep at least one login method
        has_password = user.password_hash is not None
        other_oauth_count = len(user.oauth_accounts) - 1

        if not has_password and other_oauth_count == 0:
            raise ValueError("Cannot unbind: this is your only login method. Bind an email/password first.")

        await self.oauth_repo.delete(target_oauth.id)
        await self.session.commit()

        return {"message": f"{provider} account unlinked successfully"}

    async def deactivate_account(self, user_id: int) -> bool:
        """
        Deactivate a user account.

        Args:
            user_id: User ID

        Returns:
            True if deactivated, False if not found
        """
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            return False

        # Get email for deletion
        user = await self.user_repo.deactivate_by_email(user.email)
        return user is not None

    def _hash_password(self, password: str) -> str:
        """
        Hash a password using bcrypt.

        Args:
            password: Plain text password

        Returns:
            Hashed password
        """
        return hashlib.sha256_crypt.hash(password, rounds=5000)

    def _verify_password(self, password: str, hashed_password: str) -> bool:
        """
        Verify a password against a hash.

        Args:
            password: Plain text password
            hashed_password: Hashed password to verify against

        Returns:
            True if password matches, False otherwise
        """
        try:
            return hashlib.sha256_crypt.verify(password, hashed_password)
        except (ValueError, TypeError):
            return False

    def _generate_username_from_email(self, email: str) -> str:
        """
        Generate a username from email address.

        Args:
            email: Email address

        Returns:
            Generated username
        """
        # Extract username part from email
        username = email.split('@')[0]

        # Remove special characters and limit length
        username = ''.join(c for c in username if c.isalnum() or c == '_')
        username = username[:50]

        return username or f"user_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
