import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.api.routes import auth_exchange


def test_exchange_token_returns_superuser_membership_for_whitelisted_admin(monkeypatch):
    monkeypatch.setenv("SUPER_ADMIN_EMAILS", "wxk952718180@gmail.com")
    monkeypatch.setattr(
        auth_exchange.OAuthAccount,
        "get_oauth_account",
        staticmethod(lambda provider, provider_user_id: {"user_id": 9}),
    )
    monkeypatch.setattr(
        auth_exchange.User,
        "get_user_by_id",
        staticmethod(lambda user_id: {
            "id": user_id,
            "username": "wxk952718180",
            "email": "wxk952718180@gmail.com",
            "display_name": "wxk",
            "avatar_url": None,
            "motto": "创作改变世界",
            "is_superuser": True,
            "membership_tier": "superuser",
        }),
    )
    monkeypatch.setattr(
        auth_exchange.User,
        "update_last_login",
        staticmethod(lambda user_id: True),
    )
    monkeypatch.setattr(
        auth_exchange,
        "create_access_token",
        lambda user_id: f"token-{user_id}",
    )

    response = asyncio.run(
        auth_exchange.exchange_token(
            auth_exchange.ExchangeTokenRequest(
                email="wxk952718180@gmail.com",
                name="wxk",
                google_id="google-user-1",
            )
        )
    )

    assert response.user.is_admin is True
    assert response.user.membership_tier == "superuser"
