import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import deployment.scripts.init_production_state as init_production_state


class RecordingCursor:
    def __init__(self, fetchone_results=None) -> None:
        self.calls = []
        self._fetchone_results = iter(
            fetchone_results
            or [
                {
                    "id": 42,
                    "email": "wxk952718180@gmail.com",
                    "membership_tier": "free",
                    "is_superuser": False,
                }
            ]
        )

    def execute(self, statement, params=None):
        self.calls.append((statement, params))

    def fetchone(self):
        return next(self._fetchone_results)


def test_ensure_super_admins_promotes_whitelisted_user_to_superuser_tier(monkeypatch):
    cursor = RecordingCursor()
    monkeypatch.setattr(
        "deployment.scripts.init_production_state.SUPER_ADMIN_EMAILS",
        ["wxk952718180@gmail.com"],
    )

    init_production_state.ensure_super_admins(cursor)

    update_sql, update_params = cursor.calls[1]
    assert "SET is_superuser = TRUE" in update_sql
    assert update_params[0] == "superuser"
    assert update_params[1] == 42


def test_ensure_super_admins_leaves_existing_superuser_membership_untouched(monkeypatch):
    cursor = RecordingCursor(
        fetchone_results=[
            {
                "id": 42,
                "email": "wxk952718180@gmail.com",
                "membership_tier": "superuser",
                "is_superuser": True,
            }
        ]
    )
    monkeypatch.setattr(
        "deployment.scripts.init_production_state.SUPER_ADMIN_EMAILS",
        ["wxk952718180@gmail.com"],
    )

    init_production_state.ensure_super_admins(cursor)

    assert len(cursor.calls) == 1


def test_super_admin_emails_defaults_to_empty_when_env_missing(monkeypatch):
    monkeypatch.delenv("SUPER_ADMIN_EMAILS", raising=False)

    reloaded = importlib.reload(init_production_state)

    assert reloaded.SUPER_ADMIN_EMAILS == []
