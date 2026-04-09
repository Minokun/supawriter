import asyncio
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.api.routes import articles_enhanced


class _FakeCursor:
    def __init__(self, fetchone_result=None, calls=None):
        self.fetchone_result = fetchone_result
        self.calls = calls if calls is not None else []

    def execute(self, query, params):
        self.calls.append((query, params))

    def fetchone(self):
        return self.fetchone_result

    def close(self):
        return None


class _FakeRedisClient:
    def __init__(self):
        self.progress_updates = []
        self.removals = []

    async def set_article_progress(self, article_id, data, ttl=1800):
        self.progress_updates.append((article_id, data, ttl))

    async def remove_from_queue(self, user_id, article_id):
        self.removals.append((user_id, article_id))


def test_reconcile_stale_queue_item_marks_interrupted_task_failed(monkeypatch):
    calls = []
    now = datetime(2026, 4, 5, 15, 0, tzinfo=timezone.utc)
    stale_updated_at = now - timedelta(minutes=20)
    cursors = iter([
        _FakeCursor(
            fetchone_result={
                "status": "generating",
                "topic": "僵尸任务",
                "created_at": stale_updated_at,
                "updated_at": stale_updated_at,
            },
            calls=calls,
        ),
        _FakeCursor(calls=calls),
    ])

    @contextmanager
    def fake_get_cursor(cursor_factory=None):
        yield next(cursors)

    fake_redis = _FakeRedisClient()

    monkeypatch.setattr(articles_enhanced.Database, "get_cursor", fake_get_cursor)
    monkeypatch.setattr(articles_enhanced, "redis_client", fake_redis)

    result = asyncio.run(
        articles_enhanced._reconcile_queue_item(
            user_id=9,
            article_id="task-1",
            progress={
                "status": "running",
                "progress_percent": "15",
                "current_step": "图片处理中 (1/17)",
                "topic": "僵尸任务",
            },
            now=now,
            stale_after_seconds=300,
        )
    )

    assert result is None
    assert fake_redis.removals == [(9, "task-1")]
    assert fake_redis.progress_updates == [
        (
            "task-1",
            {
                "status": "failed",
                "progress_percent": 0,
                "current_step": "任务已中断，请重试",
                "error_message": "任务在服务重载或中断后未继续执行",
                "topic": "僵尸任务",
            },
            1800,
        )
    ]
    assert "SELECT status, topic, created_at, updated_at FROM articles" in calls[0][0]
    assert "UPDATE articles" in calls[1][0]


def test_reconcile_queue_item_keeps_recent_running_task(monkeypatch):
    calls = []
    now = datetime(2026, 4, 5, 15, 0, tzinfo=timezone.utc)
    fresh_updated_at = now - timedelta(seconds=30)
    cursors = iter([
        _FakeCursor(
            fetchone_result={
                "status": "generating",
                "topic": "正常任务",
                "created_at": fresh_updated_at,
                "updated_at": fresh_updated_at,
            },
            calls=calls,
        )
    ])

    @contextmanager
    def fake_get_cursor(cursor_factory=None):
        yield next(cursors)

    fake_redis = _FakeRedisClient()

    monkeypatch.setattr(articles_enhanced.Database, "get_cursor", fake_get_cursor)
    monkeypatch.setattr(articles_enhanced, "redis_client", fake_redis)

    progress = {
        "status": "running",
        "progress_percent": "15",
        "current_step": "图片处理中 (1/17)",
        "topic": "正常任务",
        "updated_at": fresh_updated_at.isoformat(),
    }

    result = asyncio.run(
        articles_enhanced._reconcile_queue_item(
            user_id=9,
            article_id="task-2",
            progress=progress,
            now=now,
            stale_after_seconds=300,
        )
    )

    assert result == progress
    assert fake_redis.removals == []
    assert fake_redis.progress_updates == []
    assert len(calls) == 1
