# 热点数据集成实现计划

**Created**: 2026-02-28
**Status**: Draft
**Based on**: `docs/plans/2026-02-27-hotspots-integration-design.md`

---

## 概述

集成 newsnow API 作为统一热点数据源，实现热点数据的持久化存储和排名变化追踪。

## 实现步骤

### Step 1: 数据库模型 (backend/api/models/hotspot.py)

**文件**: `backend/api/models/hotspot.py`

创建三个 SQLAlchemy ORM 模型：

```python
# HotspotItem - 热点主表
# HotspotRankHistory - 排名历史表
# HotspotSource - 平台配置表
```

**字段详见设计文档**，关键约束：
- `(title, source)` 唯一约束
- 索引: `source`, `rank`, `title`

**验证**:
- 运行 `alembic revision --autogenerate -m "add hotspot tables"`
- 运行 `alembic upgrade head`

---

### Step 2: Repository 层 (backend/api/repositories/hotspot.py)

**文件**: `backend/api/repositories/hotspot.py`

继承 `BaseRepository`，实现：

| 方法 | 说明 |
|------|------|
| `get_latest_by_source(source, limit)` | 获取指定平台最新热点 |
| `get_by_title_source(title, source)` | 按标题+来源查询 |
| `update_rank(id, new_rank, new_hot_value)` | 更新排名和热度 |
| `create_with_history(item_data)` | 创建热点并记录历史 |
| `get_rank_history(item_id, hours=24)` | 获取排名历史 |
| `bulk_upsert(items)` | 批量插入或更新 |

**验证**: 单元测试 `backend/tests/test_repositories/test_hotspot.py`

---

### Step 3: Service 层 (backend/api/services/hotspots_v2_service.py)

**文件**: `backend/api/services/hotspots_v2_service.py`

```python
class HotspotsV2Service:
    """热点采集服务 v2"""

    def __init__(self, session: AsyncSession, redis: RedisClient):
        self.repo = HotspotRepository(session)
        self.redis = redis

    async def fetch_from_newsnow(source: str) -> List[dict]:
        """从 newsnow API 获取热点"""

    async def sync_source(source: str) -> SyncResult:
        """同步单个平台：获取、比较、保存、记录历史"""

    async def sync_all_sources() -> Dict[str, SyncResult]:
        """同步所有启用平台"""

    def _parse_item(raw: dict, source: str) -> HotspotItemData:
        """解析 API 响应为统一格式"""

    def _calculate_rank_change(current: int, previous: int) -> int:
        """计算排名变化"""
```

**核心逻辑**:
1. 从 newsnow API 获取数据
2. 对比数据库现有数据
3. 新增热点 → `is_new=True`
4. 已存在 → 更新 `rank`, `rank_prev`, `rank_change`
5. 记录 `hotspot_rank_history`

**验证**: 单元测试 `backend/tests/test_services/test_hotspots_v2.py`

---

### Step 4: API 路由 v2 (backend/api/routes/hotspots_v2.py)

**文件**: `backend/api/routes/hotspots_v2.py`

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/hotspots/v2/sources` | GET | 获取支持的平台列表 |
| `/api/hotspots/v2/latest` | GET | 获取所有平台最新热点 |
| `/api/hotspots/v2/latest/{source}` | GET | 获取指定平台热点 |
| `/api/hotspots/v2/history/{source}` | GET | 获取历史热点 |
| `/api/hotspots/v2/sync` | POST | 手动触发同步 (管理员) |

**响应格式**:
```json
{
  "source": "baidu",
  "updated_at": "2026-02-28T10:00:00Z",
  "items": [
    {
      "id": 1,
      "title": "热点标题",
      "rank": 1,
      "rank_change": 2,
      "is_new": false,
      "hot_value": 999999,
      "description": "描述"
    }
  ]
}
```

**验证**: 集成测试 `backend/tests/integration/test_hotspots_v2_api.py`

---

### Step 5: 定时任务 Worker (backend/api/workers/hotspots_worker.py)

**文件**: `backend/api/workers/hotspots_worker.py`

使用 APScheduler 或集成现有 arq worker：

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

@scheduler.scheduled_job('interval', minutes=10)
async def sync_hotspots_job():
    """每 10 分钟同步热点"""
    async with get_async_db_session() as session:
        service = HotspotsV2Service(session, redis_client)
        await service.sync_all_sources()
```

**配置**:
- `SYNC_INTERVAL_MINUTES` 环境变量控制间隔
- 启动时立即执行一次

---

### Step 6: 前端适配 (frontend/src/lib/api/hotspots.ts)

**文件**: `frontend/src/lib/api/hotspots.ts`

```typescript
export interface HotspotItem {
  id: number;
  title: string;
  url: string;
  source: string;
  rank: number;
  rankChange: number;
  isNew: boolean;
  hotValue: number | null;
  description: string;
}

export async function fetchHotspotsV2(source?: string): Promise<HotspotItem[]>;
export async function fetchHotspotSources(): Promise<Source[]>;
```

**UI 更新**:
- 排名变化指示器 (↑↓→ + 数字)
- 新热点标记 (NEW 标签)
- 热度值显示

---

### Step 7: 数据迁移和初始化

**SQL 脚本**:

```sql
-- 创建表
CREATE TABLE hotspot_items (...);
CREATE TABLE hotspot_rank_history (...);
CREATE TABLE hotspot_sources (...);

-- 初始化平台配置
INSERT INTO hotspot_sources (id, name, icon, enabled, sort_order, category)
VALUES
  ('baidu', '百度热搜', '🔥', true, 1, '综合'),
  ('weibo', '微博热搜', '📱', true, 2, '综合'),
  ('douyin', '抖音热搜', '🎵', true, 3, '短视频'),
  ...
```

---

### Step 8: Docker 部署配置

**文件**: `Dockerfile.hotspots`

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "-m", "backend.api.workers.hotspots_worker"]
```

**docker-compose.yml 更新**:
```yaml
  hotspots-collector:
    build:
      context: .
      dockerfile: Dockerfile.hotspots
    environment:
      - NEWSNOW_API_URL=https://newsnow.busiyi.world/api/s
      - SYNC_INTERVAL_MINUTES=10
    depends_on:
      - postgres
      - redis
```

---

## 文件清单

| 文件 | 类型 | 说明 |
|------|------|------|
| `backend/api/models/hotspot.py` | 新建 | ORM 模型 |
| `backend/api/repositories/hotspot.py` | 新建 | Repository 层 |
| `backend/api/services/hotspots_v2_service.py` | 新建 | Service 层 |
| `backend/api/routes/hotspots_v2.py` | 新建 | API 路由 v2 |
| `backend/api/workers/hotspots_worker.py` | 新建 | 定时任务 |
| `backend/api/models/__init__.py` | 修改 | 导出新模型 |
| `backend/api/main.py` | 修改 | 注册新路由 |
| `frontend/src/lib/api/hotspots.ts` | 新建 | 前端 API |
| `Dockerfile.hotspots` | 新建 | Docker 配置 |
| `docker-compose.yml` | 修改 | 添加服务 |

---

## 测试计划

| 测试类型 | 文件 | 覆盖内容 |
|---------|------|---------|
| 单元测试 | `test_repositories/test_hotspot.py` | Repository 方法 |
| 单元测试 | `test_services/test_hotspots_v2.py` | Service 逻辑 |
| 集成测试 | `test_integration/test_hotspots_v2_api.py` | API 端点 |
| E2E 测试 | Playwright | 前端热点列表 |

---

## 风险和注意事项

1. **API 限流**: newsnow API 可能有请求频率限制，需要合理设置同步间隔
2. **数据量增长**: `hotspot_rank_history` 表增长快，需要定期清理或分区
3. **并发问题**: 同步任务需要加锁防止重复执行
4. **向后兼容**: 保留 `/api/v1/hotspots` 端点，v2 作为新端点

---

## 预估工作量

| 步骤 | 预估时间 |
|------|---------|
| Step 1: 数据库模型 | 1h |
| Step 2: Repository 层 | 1.5h |
| Step 3: Service 层 | 2h |
| Step 4: API 路由 | 1h |
| Step 5: 定时任务 | 1h |
| Step 6: 前端适配 | 2h |
| Step 7: 迁移脚本 | 0.5h |
| Step 8: Docker 配置 | 0.5h |
| 测试编写 | 2h |
| **总计** | **11.5h** |