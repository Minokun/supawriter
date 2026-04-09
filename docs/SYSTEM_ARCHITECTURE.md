# SupaWriter 系统架构文档 v2.1

> **目的**：为大模型（AI 助手）后续开发提供完整的系统上下文，避免重复探索代码库。
> **更新日期**：2026-02-06
> **当前版本**：v2.1（ORM 重构 + Redis 缓存 + 性能监控）

---

## 1. 项目概览

SupaWriter（超能写手）是一个 AI 驱动的内容创作平台，包含：

| 组件 | 技术栈 | 端口 | 说明 |
|------|--------|------|------|
| **后端 API** | FastAPI + SQLAlchemy 2.0 | 8000 | 核心业务 API |
| **前端 Web** | Next.js 14 + TailwindCSS | 3000 | 社区网站 |
| **创作工具** | Streamlit | 8501 | AI 写作工具（独立部署） |
| **数据库** | PostgreSQL 14+ | 5432 | 主数据存储 |
| **缓存/限流** | Redis 6+ | 6379 | 缓存 + 分布式限流 |

**项目根目录**：`/Users/wxk/Desktop/workspace/supawriter`

---

## 2. 目录结构

```
supawriter/
├── backend/                        # 后端服务
│   ├── api/                        # FastAPI 应用
│   │   ├── main.py                 # ★ 应用入口（含中间件集成）
│   │   ├── config.py               # 旧配置（保留兼容）
│   │   ├── core/                   # 核心模块
│   │   │   ├── config.py           # ★ Pydantic Settings 配置中心
│   │   │   ├── dependencies.py     # FastAPI 依赖注入
│   │   │   ├── security.py         # JWT / 密码加密
│   │   │   ├── database.py         # 数据库初始化
│   │   │   ├── redis_manager.py    # ★ Redis 连接管理
│   │   │   ├── redis_client.py     # Redis 工具（旧）
│   │   │   ├── cache.py            # ★ 缓存装饰器 + CacheManager
│   │   │   ├── monitoring.py       # ★ Prometheus 指标收集
│   │   │   ├── encryption.py       # 数据加密
│   │   │   ├── faiss_cache.py      # FAISS 向量缓存
│   │   │   └── websocket.py        # WebSocket 管理
│   │   ├── db/                     # 数据库层
│   │   │   ├── base.py             # ★ DeclarativeBase + 引擎创建
│   │   │   ├── session.py          # ★ 同步/异步 Session 管理
│   │   │   ├── models/             # ORM 模型（见第4节）
│   │   │   └── migrations/         # Alembic 迁移
│   │   ├── repositories/           # ★ Repository 层（数据访问）
│   │   │   ├── base.py             # BaseRepository（通用 CRUD）
│   │   │   ├── user.py
│   │   │   ├── article.py
│   │   │   ├── chat.py
│   │   │   ├── quota.py
│   │   │   ├── audit.py
│   │   │   └── config.py
│   │   ├── services/               # ★ Service 层（业务逻辑）
│   │   │   ├── user.py
│   │   │   ├── article.py
│   │   │   ├── article_generator.py  # AI 文章生成
│   │   │   ├── chat.py
│   │   │   ├── quota.py
│   │   │   ├── audit.py
│   │   │   └── hotspots_service.py
│   │   ├── middleware/             # ★ 中间件
│   │   │   ├── rate_limit.py       # 限流（内存后端）
│   │   │   ├── rate_limit_redis.py # ★ 限流（Redis 后端）
│   │   │   ├── quota_check.py      # 配额检查
│   │   │   └── audit_log.py        # 审计日志
│   │   ├── routes/                 # API 路由
│   │   │   ├── auth.py             # 认证（注册/登录/OAuth）
│   │   │   ├── auth_exchange.py    # Token 交换
│   │   │   ├── articles.py         # 文章 CRUD
│   │   │   ├── articles_enhanced.py # 增强文章操作
│   │   │   ├── chat.py             # AI 聊天
│   │   │   ├── health.py           # 健康检查
│   │   │   ├── hotspots.py         # 热点话题
│   │   │   ├── news.py             # 新闻聚合
│   │   │   ├── settings.py         # 用户设置
│   │   │   └── websocket.py        # WebSocket
│   │   ├── models/                 # Pydantic 请求/响应模型
│   │   ├── utils/                  # 工具函数
│   │   └── workers/                # 后台任务
│   ├── .env                        # ★ 后端环境变量
│   ├── requirements_api.txt        # pip 依赖
│   └── tests/                      # 测试
│       ├── conftest.py             # 全局 fixture
│       ├── test_core/              # 核心模块测试
│       ├── test_models/            # 模型测试
│       ├── test_repositories/      # Repository 测试
│       ├── test_services/          # Service 测试
│       └── test_middleware/         # 中间件测试
├── frontend/                       # Next.js 前端
│   ├── src/app/                    # App Router 页面
│   ├── src/components/             # React 组件
│   └── .env.local                  # 前端环境变量
├── page/                           # Streamlit 创作工具页面
├── utils/                          # Streamlit 工具函数
├── .env                            # 根目录环境变量（JWT_SECRET_KEY）
├── .env.example                    # 环境变量模板
├── pyproject.toml                  # ★ Python 项目配置 + 依赖
├── manage.sh                       # ★ 服务管理脚本
└── monitoring/
    └── grafana-dashboard.json      # Grafana 仪表板
```

> **标注 ★ 的文件是 ORM 重构后新增或重要修改的文件。**

---

## 3. 架构分层

### 请求处理流程

```
HTTP Request
  │
  ├─→ CORS Middleware
  ├─→ Session Middleware
  ├─→ Audit Log Middleware        ← 记录请求/响应
  ├─→ Rate Limit Middleware       ← Redis ZSET 滑动窗口
  │
  ▼
Route Handler (FastAPI)
  │
  ├─→ Depends(get_current_user)   ← JWT 认证
  ├─→ Depends(get_db)             ← AsyncSession 注入
  │
  ▼
Service Layer                      ← 业务逻辑
  │
  ├─→ Cache Layer (Redis)          ← @cache 装饰器
  │
  ▼
Repository Layer                   ← 数据访问
  │
  ▼
SQLAlchemy ORM → PostgreSQL
```

### 各层职责

| 层 | 位置 | 职责 | 规则 |
|----|------|------|------|
| **Route** | `routes/` | 请求解析、参数校验、响应格式化 | 不含业务逻辑 |
| **Service** | `services/` | 业务逻辑、事务编排、缓存调用 | 不直接操作 DB |
| **Repository** | `repositories/` | SQL 查询、CRUD 操作 | 不含业务逻辑 |
| **Model** | `db/models/` | ORM 映射、字段定义、关系 | 纯数据结构 |
| **Middleware** | `middleware/` | 横切关注点（限流/审计/配额） | 不依赖 Service |

---

## 4. 数据模型

### ORM 模型一览

所有模型位于 `backend/api/db/models/`，继承自 `Base`（DeclarativeBase）。

| 模型 | 文件 | 表名 | 主键类型 | 说明 |
|------|------|------|---------|------|
| `User` | `user.py` | `users` | int | 用户 |
| `OAuthAccount` | `user.py` | `oauth_accounts` | int | OAuth 关联 |
| `Article` | `article.py` | `articles` | **UUID** | 文章（分布式安全） |
| `ChatSession` | `chat.py` | `chat_sessions` | int | 聊天会话 |
| `ChatMessage` | `chat.py` | `chat_messages` | int | 聊天消息 |
| `QuotaUsage` | `quota.py` | `quota_usages` | int | 配额使用记录 |
| `QuotaPlan` | `quota.py` | `quota_plans` | int | 配额计划 |
| `AuditLog` | `audit.py` | `audit_logs` | int | 审计日志 |
| `UserConfig` | `config.py` | `user_configs` | int | 用户配置 |
| `ApiKey` | `config.py` | `api_keys` | int | API 密钥 |
| `SystemConfig` | `system.py` | `system_configs` | int | 系统配置 |

### Base 类和 Mixin

```python
# backend/api/db/base.py

class Base(DeclarativeBase):
    """所有 ORM 模型的基类"""
    pass

class BaseModel:
    """Mixin：提供 id(int), created_at, updated_at"""
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]
```

> **注意**：`Article` 模型不继承 `BaseModel`，因为它使用 UUID 主键。

### 数据库连接

```python
# backend/api/db/base.py
engine = create_db_engine()           # 同步引擎（Worker 用）
async_engine = create_async_db_engine()  # 异步引擎（FastAPI 用）

# backend/api/db/session.py
SessionLocal          # 同步 Session（scoped_session）
AsyncSessionLocal     # 异步 Session（async_sessionmaker）

get_db_session()      # 同步上下文管理器
get_async_db_session() # 异步上下文管理器
get_db()              # FastAPI 依赖注入
```

数据库 URL 构建优先级：
1. 环境变量 `DATABASE_URL`（完整 URL）
2. `POSTGRES_HOST` / `POSTGRES_PORT` / `POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD`（组合）

---

## 5. 配置系统

### 配置架构（Pydantic Settings）

配置中心位于 `backend/api/core/config.py`，使用嵌套的 Pydantic Settings 类：

```
AppConfig                          ← 主配置（单例）
├── database: DatabaseConfig       ← env_prefix="POSTGRES_"
├── redis: RedisConfig             ← env_prefix="REDIS_"
├── rate_limit: RateLimitConfig    ← env_prefix="RATE_LIMIT_"
├── quota: QuotaConfig             ← env_prefix="QUOTA_"
├── audit: AuditConfig             ← env_prefix="AUDIT_"
├── cache: CacheConfig             ← env_prefix="CACHE_"
└── monitoring: MonitoringConfig   ← env_prefix="MONITORING_"
```

### 使用方式

```python
from backend.api.core.config import get_settings

settings = get_settings()  # 单例
settings.database.get_url()
settings.redis.get_url()
settings.rate_limit.requests_per_minute
settings.cache.default_ttl
```

### 环境变量文件

| 文件 | 用途 | 加载方式 |
|------|------|---------|
| `.env` | 根目录全局配置（JWT_SECRET_KEY, DATABASE_URL） | 旧代码 `os.getenv()` |
| `backend/.env` | 后端 ORM 配置（Pydantic Settings 自动加载） | `AppConfig(env_file=".env")` |
| `frontend/.env.local` | 前端配置（NEXTAUTH_SECRET 等） | Next.js 自动加载 |
| `.env.example` | 环境变量模板 | 手动复制 |

> **重要**：`backend/.env` 是后端的主配置文件，`AppConfig` 会自动从中加载。根目录 `.env` 是旧代码兼容用的。

---

## 6. API 路由

### 路由注册（main.py）

```python
app.include_router(health.router)                                    # /health
app.include_router(auth.router, prefix="/api/v1/auth")               # /api/v1/auth
app.include_router(auth_exchange.router, prefix="/api/v1/auth")      # /api/v1/auth
app.include_router(articles.router, prefix="/api/v1/articles")       # /api/v1/articles
app.include_router(articles_enhanced.router, prefix="/api/v1/articles")
app.include_router(chat.router, prefix="/api/v1/chat")               # /api/v1/chat
app.include_router(hotspots.router, prefix="/api/v1/hotspots")       # /api/v1/hotspots
app.include_router(news.router, prefix="/api/v1/news")               # /api/v1/news
app.include_router(websocket.router, prefix="/api/v1")               # /api/v1/ws
app.include_router(settings_route.router, prefix="/api/v1/settings") # /api/v1/settings
```

### 健康检查端点

| 端点 | 用途 |
|------|------|
| `GET /health` | 基础健康检查（不查 DB） |
| `GET /health/database` | 数据库连接 + 延迟检测 |
| `GET /health/full` | 完整健康检查 |
| `GET /health/ready` | Kubernetes 就绪探针 |
| `GET /health/live` | Kubernetes 存活探针 |
| `GET /metrics` | Prometheus 指标 |

---

## 7. 中间件

### 中间件栈（执行顺序从外到内）

```
SessionMiddleware          ← OAuth Session 支持
CORSMiddleware             ← 跨域
AuditLogMiddleware         ← 审计日志（如果启用）
RateLimitMiddleware        ← 限流（如果启用）
```

### 限流器

| 实现 | 文件 | 后端 | 适用场景 |
|------|------|------|---------|
| `RateLimiterMemory` | `rate_limit.py` | 内存 dict | 开发/单实例 |
| `RateLimiterRedis` | `rate_limit_redis.py` | Redis ZSET | **生产/多实例** |

选择逻辑（`main.py`）：
- `RATE_LIMIT_USE_REDIS=true` + Redis 可用 → 使用 Redis 限流
- 否则 → 降级为内存限流

### 中间件依赖注入

中间件不能使用 FastAPI 的 `Depends()`，因此使用**服务工厂模式**：

```python
class GlobalServices:
    @staticmethod
    async def get_audit_service():
        async with get_async_db_session() as session:
            audit_repo = AuditLogRepository(session)
            return AuditService(session, audit_repo)
```

---

## 8. 缓存系统

### 缓存装饰器

```python
from backend.api.core.cache import cache

@cache(ttl=300)                          # 缓存 5 分钟
async def get_user(user_id: int):
    return await user_repo.get_by_id(user_id)

@cache(ttl=60, key_prefix="quota")       # 缓存 1 分钟
async def get_quota(user_id: int, quota_type: str):
    return await quota_service.get_quota_info(user_id, quota_type)
```

### CacheManager

```python
from backend.api.core.cache import get_cache_manager

cache_mgr = get_cache_manager()
await cache_mgr.get_user(user_id)
await cache_mgr.invalidate_user(user_id)
await cache_mgr.invalidate_article_list(user_id)
```

### 缓存 TTL 策略

| 数据类型 | TTL | 环境变量 | 失效时机 |
|---------|-----|---------|---------|
| 用户信息 | 600s | `CACHE_USER_TTL` | 用户更新时 |
| 配额信息 | 60s | `CACHE_QUOTA_TTL` | 配额消费时 |
| 文章列表 | 300s | `CACHE_ARTICLE_LIST_TTL` | 文章增删时 |

### 降级策略

Redis 不可用时，缓存装饰器自动跳过缓存，直接调用原函数。不会抛出异常。

---

## 9. 监控系统

### Prometheus 指标（`/metrics`）

| 指标名 | 类型 | 标签 | 说明 |
|--------|------|------|------|
| `api_requests_total` | Counter | method, endpoint, status | 请求总数 |
| `api_request_duration_seconds` | Histogram | method, endpoint | 请求延迟 |
| `db_queries_total` | Counter | operation, table | DB 查询数 |
| `db_query_duration_seconds` | Histogram | operation, table | DB 查询延迟 |
| `db_slow_queries_total` | Counter | operation, table | 慢查询数 |
| `db_pool_size` | Gauge | — | 连接池大小 |
| `db_pool_checked_in` | Gauge | — | 空闲连接数 |
| `db_pool_overflow` | Gauge | — | 溢出连接数 |
| `cache_hits_total` | Counter | cache_type | 缓存命中 |
| `cache_misses_total` | Counter | cache_type | 缓存未命中 |
| `rate_limit_exceeded_total` | Counter | endpoint | 限流触发 |
| `quota_exceeded_total` | Counter | quota_type | 配额超限 |

### 使用方式

```python
from backend.api.core.monitoring import get_metrics_collector

collector = get_metrics_collector()
collector.record_request("GET", "/api/v1/users", 200, 0.123)
collector.record_db_query("SELECT", "users", 0.045)
collector.record_cache_hit("user")
```

---

## 10. 认证系统

### JWT 认证流程

```
POST /api/v1/auth/login
  → 验证用户名/密码
  → 生成 JWT Token（含 user_id）
  → 返回 { access_token, token_type }

后续请求:
  Header: Authorization: Bearer <token>
  → get_current_user() 依赖解析 user_id
```

### 关键函数

| 函数 | 文件 | 说明 |
|------|------|------|
| `get_current_user()` | `core/dependencies.py` | 必须认证 |
| `get_current_user_optional()` | `core/dependencies.py` | 可选认证 |
| `get_ws_user()` | `core/dependencies.py` | WebSocket 认证 |
| `verify_token()` | `core/security.py` | JWT 验证 |
| `create_access_token()` | `core/security.py` | JWT 生成 |
| `get_db()` | `core/dependencies.py` | DB Session 注入 |

---

## 11. 依赖管理

### Python 依赖

项目使用 **uv** 管理 Python 依赖，配置在 `pyproject.toml`：

```bash
uv sync          # 同步所有依赖（推荐）
uv run <cmd>     # 在虚拟环境中运行命令
```

### 关键依赖

| 包 | 版本 | 用途 |
|----|------|------|
| `fastapi` | ≥0.95 | Web 框架 |
| `uvicorn` | ≥0.20 | ASGI 服务器 |
| `sqlalchemy` | ≥2.0.35 | ORM |
| `asyncpg` | ≥0.29 | PostgreSQL 异步驱动 |
| `alembic` | ≥1.13 | 数据库迁移 |
| `redis` | ≥4.5 | Redis 客户端 |
| `pydantic-settings` | ≥2.0 | 配置管理 |
| `prometheus-client` | ≥0.20 | 监控指标 |
| `pyjwt` | ≥2.8 | JWT |
| `passlib` | ≥1.7 | 密码哈希 |

### 前端依赖

```bash
cd frontend && npm install
```

---

## 12. 服务管理

### manage.sh 命令速查

```bash
./manage.sh start                  # 启动全部（后端 + 前端）
./manage.sh start backend          # 仅启动后端
./manage.sh stop                   # 停止全部
./manage.sh restart backend        # 重启后端
./manage.sh status                 # 查看状态（含 PostgreSQL/Redis）
./manage.sh health                 # API 健康检查
./manage.sh logs backend 100       # 查看后端最近 100 行日志
./manage.sh test core              # 运行核心模块测试
./manage.sh test repos             # 运行 Repository 测试
./manage.sh db upgrade             # 执行数据库迁移
./manage.sh db history             # 查看迁移历史
./manage.sh install                # 安装依赖 + 配置环境
./manage.sh clean                  # 清理缓存和临时文件
```

### 手动启动

```bash
# 后端
uv run uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --reload --reload-dir backend

# 前端
cd frontend && npm run dev
```

---

## 13. 测试

### 测试结构

```
backend/tests/
├── conftest.py                    # 全局 fixture（app, client, db session）
├── test_core/
│   ├── test_config.py             # 配置模块测试
│   └── test_cache.py              # 缓存模块测试
├── test_models/
│   ├── test_article.py            # Article 模型测试
│   ├── test_user.py               # User 模型测试
│   └── ...
├── test_repositories/
│   ├── conftest.py                # Repository fixture
│   ├── test_article.py
│   ├── test_user.py
│   └── ...
├── test_services/
│   ├── conftest.py                # Service fixture
│   ├── test_article.py
│   ├── test_chat.py
│   └── ...
└── test_middleware/
    ├── test_rate_limit.py
    ├── test_rate_limit_redis.py   # Redis 限流测试
    └── ...
```

### 运行测试

```bash
./manage.sh test all               # 全部
./manage.sh test core              # 核心模块
./manage.sh test models            # 模型
./manage.sh test repos             # Repository
./manage.sh test services          # Service
./manage.sh test middleware        # 中间件

# 或直接使用 pytest
uv run pytest backend/tests/ -v --tb=short
uv run pytest backend/tests/test_core/test_config.py -v
```

---

## 14. 开发规范

### 新增 API 端点的标准流程

1. **定义 ORM 模型**（如需新表）→ `db/models/xxx.py`
2. **创建 Repository** → `repositories/xxx.py`（继承 `BaseRepository`）
3. **创建 Service** → `services/xxx.py`（注入 Repository）
4. **创建 Route** → `routes/xxx.py`（注入 Service，使用 `Depends`）
5. **注册路由** → `main.py` 中 `app.include_router()`
6. **添加测试** → `tests/test_xxx/`
7. **数据库迁移** → `alembic revision --autogenerate -m "xxx"`

### Repository 模式示例

```python
# repositories/article.py
class ArticleRepository(BaseRepository[Article]):
    def __init__(self, session: AsyncSession):
        super().__init__(Article, session)

    async def get_by_user(self, user_id: int, skip=0, limit=20):
        stmt = select(Article).where(Article.user_id == user_id).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()
```

### Service 模式示例

```python
# services/article.py
class ArticleService:
    def __init__(self, session: AsyncSession, article_repo: ArticleRepository):
        self.session = session
        self.article_repo = article_repo

    async def create_article(self, user_id: int, data: dict) -> Article:
        article = Article(user_id=user_id, **data)
        return await self.article_repo.create(article)
```

### 缓存使用规范

```python
# 读操作：使用 @cache 装饰器
@cache(ttl=300)
async def get_article(article_id: str):
    return await article_repo.get_by_id(article_id)

# 写操作：手动失效缓存
async def update_article(article_id: str, data: dict):
    result = await article_repo.update(article_id, data)
    cache_mgr = get_cache_manager()
    await cache_mgr.invalidate_article_list(result.user_id)
    return result
```

---

## 15. 已知问题和注意事项

### 双 .env 文件

项目存在两个 `.env` 文件：
- **根目录 `.env`**：旧代码使用 `os.getenv()` 读取（`JWT_SECRET_KEY`, `DATABASE_URL`）
- **`backend/.env`**：新 ORM 配置使用 Pydantic Settings 读取

两者需要保持数据库连接信息一致。长期应统一为 `backend/.env`。

### Redis 可选

Redis 不是必须的。未运行时：
- 限流降级为内存模式（单实例有效）
- 缓存装饰器自动跳过（直接查 DB）
- 不影响核心功能

### 旧文件保留

以下文件是重构前的备份，保留用于参考：
- `backend/api/main_old.py` — 旧版主应用
- `backend/api/main_original_backup.py` — 原始备份
- `backend/api/routes/articles_old.py` — 旧版文章路由
- `backend/api/routes/auth_old.py` — 旧版认证路由

### 中间件异步依赖

FastAPI 中间件不支持 `Depends()` 注入，当前使用 `GlobalServices` 工厂模式解决。如果需要在中间件中访问数据库，必须通过 `get_async_db_session()` 手动创建 session。

---

## 16. 快速参考卡片

### 常用导入

```python
# 配置
from backend.api.core.config import get_settings

# 数据库
from backend.api.db.session import get_async_db_session, get_db
from backend.api.db.base import Base, BaseModel

# 认证
from backend.api.core.dependencies import get_current_user, get_db

# 缓存
from backend.api.core.cache import cache, get_cache_manager

# 监控
from backend.api.core.monitoring import get_metrics_collector

# Redis
from backend.api.core.redis_manager import get_redis_manager
```

### 环境变量速查

```bash
# 必须配置
POSTGRES_HOST / POSTGRES_PORT / POSTGRES_DB / POSTGRES_USER / POSTGRES_PASSWORD
# 或
DATABASE_URL=postgresql://user:pass@host:port/db

# 可选配置
REDIS_HOST=localhost                    # Redis 地址
RATE_LIMIT_ENABLED=true                 # 启用限流
RATE_LIMIT_USE_REDIS=true               # 使用 Redis 限流
CACHE_ENABLED=true                      # 启用缓存
MONITORING_ENABLED=true                 # 启用监控
MONITORING_PROMETHEUS_ENABLED=true      # 启用 Prometheus
DEBUG=true                              # 调试模式
```

### 端口速查

| 服务 | 端口 | URL |
|------|------|-----|
| 后端 API | 8000 | http://localhost:8000 |
| API 文档 | 8000 | http://localhost:8000/docs |
| Prometheus | 8000 | http://localhost:8000/metrics |
| 前端 Web | 3000 | http://localhost:3000 |
| PostgreSQL | 5432 | — |
| Redis | 6379 | — |

---

## 17. 相关文档索引

| 文档 | 路径 | 说明 |
|------|------|------|
| 本文档 | `docs/SYSTEM_ARCHITECTURE.md` | 系统架构（大模型参考） |
| 实施计划 | `docs/plans/2026-02-05-backend-orm-refactor-implementation.md` | ORM 重构实施计划 |
| 代码审查 | `docs/ORM_REFACTOR_CODE_REVIEW_WORKTREE.md` | 代码审查报告 |
| 修复优化 | `docs/ORM_REFACTOR_FIXES_AND_OPTIMIZATIONS.md` | 修复和优化详情 |
| 实施总结 | `docs/ORM_REFACTOR_SUMMARY.md` | ORM 重构总结 |
| 环境模板 | `.env.example` | 环境变量完整模板 |
| README | `README_ORM_REFACTOR.md` | ORM 重构使用指南 |
| Grafana | `monitoring/grafana-dashboard.json` | 监控仪表板 |

---

*本文档由 Cascade AI 生成，供后续大模型开发时作为系统上下文参考。*
