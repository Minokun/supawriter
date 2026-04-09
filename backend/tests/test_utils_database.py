from contextlib import contextmanager

import psycopg2

from utils.database import OAuthAccount, Database


class _FakeCursor:
    def __init__(self, calls, fetchone_result=None, fail_with_undefined_column=False):
        self.calls = calls
        self.fetchone_result = fetchone_result or {"id": 7}
        self.fail_with_undefined_column = fail_with_undefined_column

    def execute(self, query, params):
        self.calls.append((query, params))
        if self.fail_with_undefined_column:
            raise psycopg2.errors.UndefinedColumn(
                'column "extra_data" of relation "oauth_accounts" does not exist'
            )

    def fetchone(self):
        return self.fetchone_result

    def close(self):
        return None


def test_create_oauth_account_skips_extra_data_when_column_is_missing(monkeypatch):
    calls = []
    OAuthAccount._has_extra_data_column = None
    cursors = iter(
        [
            _FakeCursor(calls, fetchone_result={"exists": False}),
            _FakeCursor(calls, fetchone_result={"id": 7}),
        ]
    )

    @contextmanager
    def fake_get_cursor(cursor_factory=None):
        yield next(cursors)

    monkeypatch.setattr(Database, "get_cursor", fake_get_cursor)

    oauth_id = OAuthAccount.create_oauth_account(
        user_id=9,
        provider="google",
        provider_user_id="google-user-1",
        extra_data={"email": "wxk952718180@gmail.com"},
    )

    assert oauth_id == 7
    assert "information_schema.columns" in calls[0][0]
    assert "extra_data" not in calls[1][0]
