from types import SimpleNamespace
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.api.routes import auth


@pytest.mark.asyncio
async def test_login_returns_membership_tier_and_admin_flag(monkeypatch):
    monkeypatch.setattr(auth, "create_access_token", lambda user_id: f"token-{user_id}")

    class StubUserService:
        async def authenticate_user(self, email: str, password: str):
            assert email == "admin@example.com"
            assert password == "secret123"
            return SimpleNamespace(
                id=42,
                username="admin-user",
                email="admin@example.com",
                display_name="Admin User",
                avatar_url=None,
                motto="创作改变世界",
                is_superuser=True,
                membership_tier="superuser",
            )

    monkeypatch.setattr(
        "backend.api.services.tier_service.get_super_admin_emails",
        lambda: {"admin@example.com"},
    )

    response = await auth.login(
        auth.LoginRequest(email="admin@example.com", password="secret123"),
        user_service=StubUserService(),
    )

    assert response.access_token == "token-42"
    assert response.user.membership_tier == "superuser"
    assert response.user.is_admin is True
