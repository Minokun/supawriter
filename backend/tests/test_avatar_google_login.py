"""
Regression test for avatar display after Google login.

Bug: After Google OAuth login, the avatar in the top-right corner showed 👤
instead of the Google profile photo.

Root cause: When the NextAuth session was authenticated, the useAuth hook
called persistBackendAuth(sessionToken) WITHOUT user info. This meant
userInfo was null until fetchUserInfo() completed (async /auth/me call).
During this gap, resolveUserAvatar had both backendAvatar=null and
sessionAvatar=undefined, so the avatar showed the fallback emoji.

Fix: Build optimistic userInfo from session.user immediately when the
NextAuth session is authenticated, so the avatar is available from the
first authenticated render.

This test verifies the backend data flow is correct (avatar is returned
by exchange-token and _build_user_info correctly maps avatar_url → avatar).
"""
from types import SimpleNamespace
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.api.routes import auth_exchange
from backend.api.routes import auth


def test_build_user_info_maps_avatar_url_to_avatar():
    """_build_user_info must map the DB field avatar_url to UserInfo.avatar."""
    user_dict = {
        "id": 1,
        "username": "testuser",
        "email": "test@example.com",
        "display_name": "Test User",
        "avatar_url": "https://lh3.googleusercontent.com/test-photo=s96-c",
        "motto": "hello",
        "is_superuser": False,
        "membership_tier": "free",
    }
    info = auth_exchange._build_user_info(user_dict)
    assert info.avatar == "https://lh3.googleusercontent.com/test-photo=s96-c"


def test_build_user_info_handles_null_avatar():
    """_build_user_info must handle null avatar_url gracefully."""
    user_dict = {
        "id": 2,
        "username": "noavatar",
        "email": "noavatar@example.com",
        "display_name": None,
        "avatar_url": None,
        "motto": "hello",
        "is_superuser": False,
        "membership_tier": "free",
    }
    info = auth_exchange._build_user_info(user_dict)
    assert info.avatar is None


def test_user_to_user_info_maps_avatar_url():
    """auth._user_to_user_info must also map avatar_url to avatar."""
    user_dict = {
        "id": 3,
        "username": "mapper",
        "email": "mapper@example.com",
        "display_name": "Mapper",
        "avatar_url": "https://cdn.example.com/custom-avatar.png",
        "motto": "map it",
        "is_superuser": False,
        "membership_tier": "pro",
    }
    info = auth._user_to_user_info(user_dict)
    assert info.avatar == "https://cdn.example.com/custom-avatar.png"
