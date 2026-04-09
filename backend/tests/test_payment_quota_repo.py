import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.api.repositories.payment import QuotaPackRepository


class DummyResult:
    def scalar(self):
        return 6


class DummySession:
    def __init__(self):
        self.statement = None

    async def execute(self, statement):
        self.statement = statement
        return DummyResult()


@pytest.mark.asyncio
async def test_get_total_remaining_quota_aggregates_remaining_quota():
    session = DummySession()
    repo = QuotaPackRepository(session)

    total = await repo.get_total_remaining_quota(11)

    assert total == 6
    assert "sum(quota_packs.remaining_quota)" in str(session.statement)
