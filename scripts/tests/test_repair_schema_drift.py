import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from deployment.scripts.repair_schema_drift import ensure_users_columns


class RecordingCursor:
    def __init__(self) -> None:
        self.statements: list[str] = []

    def execute(self, statement: str) -> None:
        self.statements.append(statement)


def test_ensure_users_columns_adds_all_runtime_required_fields() -> None:
    cursor = RecordingCursor()

    ensure_users_columns(cursor)

    expected_fragments = [
        "ADD COLUMN IF NOT EXISTS avatar_source",
        "ADD COLUMN IF NOT EXISTS phone VARCHAR(20)",
        "ADD COLUMN IF NOT EXISTS phone_verified BOOLEAN DEFAULT FALSE",
        "ADD COLUMN IF NOT EXISTS email_verified BOOLEAN DEFAULT FALSE",
        "ADD COLUMN IF NOT EXISTS is_superuser BOOLEAN DEFAULT FALSE",
    ]

    executed_sql = "\n".join(cursor.statements)

    for fragment in expected_fragments:
        assert fragment in executed_sql


def test_ensure_users_columns_repairs_membership_tier_constraint() -> None:
    cursor = RecordingCursor()

    ensure_users_columns(cursor)

    executed_sql = "\n".join(cursor.statements)

    assert "DROP CONSTRAINT IF EXISTS check_membership_tier" in executed_sql
    assert "membership_tier IN ('free', 'pro', 'ultra', 'superuser')" in executed_sql
