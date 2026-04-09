# P2 技术设计文档 — 生态闭环

> **创建日期**: 2026-02-15
> **版本**: v1.0
> **关联PRD**: `docs/plans/2026-02-15-p2-prd.md`
> **关联总纲**: `docs/plans/2026-02-15-development-master-plan.md`
> **前置**: P0 + P1 全部功能已上线

---

## 一、架构总览

### 1.1 P2 功能在系统中的位置

```
┌─────────────────── Frontend (Next.js) ───────────────────┐
│                                                          │
│  文章页(扩展)   知识库页(新)  团队页(新)   日历页(新)      │
│  ┌──────┐     ┌──────┐    ┌──────┐    ┌──────┐         │
│  │F13:  │     │F14:  │    │F15:  │    │F16:  │         │
│  │发布   │     │知识库 │    │团队   │    │日历   │         │
│  │面板   │     │管理   │    │协作   │    │排期   │         │
│  └──────┘     └──────┘    └──────┘    └──────┘         │
│                                                          │
│  设置页(扩展)        API文档页(新)                         │
│  ┌──────┐          ┌──────┐                              │
│  │平台   │          │F17:  │                              │
│  │绑定   │          │API   │                              │
│  │管理   │          │文档   │                              │
│  └──────┘          └──────┘                              │
└──────────────────────────────────────────────────────────┘
                          │
                    API Layer
                          │
┌─────────────────── Backend (FastAPI) ────────────────────┐
│                                                          │
│  routes/                                                 │
│  ├── platforms.py       (新增: 平台绑定+发布API)          │
│  ├── knowledge_base.py  (新增: 知识库CRUD+搜索)          │
│  ├── teams.py           (新增: 团队管理+审批)             │
│  ├── calendar.py        (新增: 内容日历API)               │
│  └── open_api.py        (新增: 开放API v1)               │
│                                                          │
│  services/                                               │
│  ├── publisher_service.py   (新增: 多平台发布编排)        │
│  ├── knowledge_base.py      (新增: 文档解析+向量化+RAG)   │
│  ├── team_service.py        (新增: 团队+审批逻辑)         │
│  ├── calendar_service.py    (新增: 排期+节日管理)         │
│  └── open_api_service.py    (新增: API计量+限流)          │
│                                                          │
│  workers/                                                │
│  ├── publish_worker.py      (新增: 定时发布任务)          │
│  └── vectorize_worker.py    (新增: 文档向量化任务)        │
└──────────────────────────────────────────────────────────┘
```

### 1.2 新增/修改文件清单

| 类型 | 文件路径 | 操作 | 说明 |
|------|---------|------|------|
| **后端-路由** | `backend/api/routes/platforms.py` | 新增 | 平台绑定+发布 |
| **后端-路由** | `backend/api/routes/knowledge_base.py` | 新增 | 知识库CRUD |
| **后端-路由** | `backend/api/routes/teams.py` | 新增 | 团队管理+审批 |
| **后端-路由** | `backend/api/routes/calendar.py` | 新增 | 内容日历 |
| **后端-路由** | `backend/api/routes/open_api.py` | 新增 | 开放API |
| **后端-服务** | `backend/api/services/publisher_service.py` | 新增 | 多平台发布 |
| **后端-服务** | `backend/api/services/knowledge_base.py` | 新增 | 知识库核心 |
| **后端-服务** | `backend/api/services/team_service.py` | 新增 | 团队协作 |
| **后端-服务** | `backend/api/services/calendar_service.py` | 新增 | 日历排期 |
| **后端-服务** | `backend/api/services/open_api_service.py` | 新增 | API计量 |
| **后端-Worker** | `backend/api/workers/publish_worker.py` | 新增 | 定时发布 |
| **后端-Worker** | `backend/api/workers/vectorize_worker.py` | 新增 | 文档向量化 |
| **后端-Worker** | `backend/api/workers/article_worker.py` | 修改 | 集成知识库RAG |
| **前端-页面** | `frontend/src/app/knowledge-base/page.tsx` | 新增 | 知识库管理 |
| **前端-页面** | `frontend/src/app/team/page.tsx` | 新增 | 团队管理 |
| **前端-页面** | `frontend/src/app/calendar/page.tsx` | 新增 | 内容日历 |
| **前端-页面** | `frontend/src/app/api-docs/page.tsx` | 新增 | API文档 |
| **前端-组件** | `frontend/src/components/publish/PublishPanel.tsx` | 新增 | 发布面板 |
| **数据库** | `deployment/migrate/010_p2_features.sql` | 新增 | P2数据库迁移 |

---

## 二、数据库变更

### 2.1 新增表

#### platform_connections — 平台绑定

```sql
CREATE TABLE IF NOT EXISTS platform_connections (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    platform VARCHAR(20) NOT NULL CHECK (platform IN ('wechat_mp', 'toutiao', 'zhihu')),
    platform_user_id VARCHAR(255),
    platform_username VARCHAR(255),
    access_token TEXT NOT NULL,
    refresh_token TEXT,
    token_expires_at TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_user_platform UNIQUE (user_id, platform)
);
```

#### publish_logs — 发布日志

```sql
CREATE TABLE IF NOT EXISTS publish_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    article_id INTEGER NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
    platform VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL CHECK (status IN ('pending', 'published', 'failed', 'scheduled')),
    external_id VARCHAR(255),
    external_url TEXT,
    error_message TEXT,
    scheduled_at TIMESTAMPTZ,
    published_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_publish_logs_article ON publish_logs(article_id);
```

#### knowledge_documents — 知识库文档

```sql
CREATE TABLE IF NOT EXISTS knowledge_documents (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    team_id INTEGER REFERENCES teams(id) ON DELETE CASCADE,
    filename VARCHAR(255) NOT NULL,
    file_type VARCHAR(20) NOT NULL,
    file_size INTEGER NOT NULL,
    chunk_count INTEGER DEFAULT 0,
    vectorized BOOLEAN DEFAULT FALSE,
    source_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_knowledge_docs_user ON knowledge_documents(user_id);
```

#### document_chunks — 文档分块（向量化后）

```sql
CREATE TABLE IF NOT EXISTS document_chunks (
    id SERIAL PRIMARY KEY,
    document_id INTEGER NOT NULL REFERENCES knowledge_documents(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding_vector BYTEA,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_chunks_document ON document_chunks(document_id);
CREATE INDEX idx_chunks_user ON document_chunks(user_id);
```

#### teams — 团队

```sql
CREATE TABLE IF NOT EXISTS teams (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    logo_url TEXT,
    owner_id INTEGER NOT NULL REFERENCES users(id),
    max_members INTEGER DEFAULT 10,
    style_profile JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

#### team_members — 团队成员

```sql
CREATE TABLE IF NOT EXISTS team_members (
    id SERIAL PRIMARY KEY,
    team_id INTEGER NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL CHECK (role IN ('owner', 'admin', 'editor', 'viewer')),
    joined_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_team_member UNIQUE (team_id, user_id)
);

CREATE INDEX idx_team_members_user ON team_members(user_id);
```

#### team_invitations — 团队邀请

```sql
CREATE TABLE IF NOT EXISTS team_invitations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_id INTEGER NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'editor',
    invited_by INTEGER NOT NULL REFERENCES users(id),
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'accepted', 'expired')),
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

#### article_approvals — 文章审批

```sql
CREATE TABLE IF NOT EXISTS article_approvals (
    id SERIAL PRIMARY KEY,
    article_id INTEGER NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
    team_id INTEGER NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    submitted_by INTEGER NOT NULL REFERENCES users(id),
    reviewed_by INTEGER REFERENCES users(id),
    status VARCHAR(20) NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'approved', 'rejected')),
    review_comment TEXT,
    submitted_at TIMESTAMPTZ DEFAULT NOW(),
    reviewed_at TIMESTAMPTZ
);

CREATE INDEX idx_approvals_team ON article_approvals(team_id, status);
```

#### content_calendar — 内容排期

```sql
CREATE TABLE IF NOT EXISTS content_calendar (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    team_id INTEGER REFERENCES teams(id) ON DELETE CASCADE,
    article_id INTEGER REFERENCES articles(id) ON DELETE SET NULL,
    scheduled_date DATE NOT NULL,
    title VARCHAR(500),
    status VARCHAR(20) DEFAULT 'planned'
        CHECK (status IN ('planned', 'draft', 'scheduled', 'published')),
    platforms TEXT[] DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_calendar_user_date ON content_calendar(user_id, scheduled_date);
```

#### calendar_events — 节日/营销节点

```sql
CREATE TABLE IF NOT EXISTS calendar_events (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    event_date DATE NOT NULL,
    event_type VARCHAR(20) NOT NULL
        CHECK (event_type IN ('holiday', 'solar_term', 'ecommerce', 'industry', 'custom')),
    description TEXT,
    content_suggestions TEXT[],
    is_recurring BOOLEAN DEFAULT TRUE,
    CONSTRAINT uq_event_date_name UNIQUE (event_date, name)
);
```

#### api_usage_logs — API调用日志

```sql
CREATE TABLE IF NOT EXISTS api_usage_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    api_key_id INTEGER,
    endpoint VARCHAR(100) NOT NULL,
    status_code INTEGER,
    response_time_ms INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_api_usage_user_date ON api_usage_logs(user_id, created_at);
```

---

## 三、核心服务设计

### 3.1 多平台发布服务

```python
class PublisherService:
    """
    多平台发布编排器
    
    设计原则:
    - 每个平台一个适配器（Strategy模式）
    - 发布前自动格式转换（复用P0 PlatformConverter）
    - 支持同步发布和定时发布
    - 发布结果记录到publish_logs
    """
    
    ADAPTERS = {
        'wechat_mp': WechatMPAdapter,
        'toutiao': ToutiaoAdapter,
        'zhihu': ZhihuAdapter,
    }
    
    async def publish(self, article_id, platforms, user_id, scheduled_at=None):
        results = []
        for platform in platforms:
            adapter = self.ADAPTERS[platform]()
            connection = await self._get_connection(user_id, platform)
            
            # 1. 格式转换
            converted = await platform_converter.convert(content, platform)
            
            # 2. 发布
            if scheduled_at:
                await self._schedule_publish(article_id, platform, scheduled_at)
            else:
                result = await adapter.publish_draft(connection, converted)
                results.append(result)
            
            # 3. 记录日志
            await self._log_publish(article_id, platform, result)
        
        return results
```

### 3.2 知识库服务（RAG）

```python
class KnowledgeBaseService:
    """
    知识库服务
    
    流程:
    1. 上传: 文档解析 → 分块 → 向量化 → 存储
    2. 检索: 查询向量化 → FAISS相似度搜索 → 返回Top-K
    3. 生成: 检索结果作为context注入prompt（RAG模式）
    
    复用:
    - FAISS: 复用现有 faiss_cache.py 的向量索引能力
    - Embedding: 复用现有 embedding_utils.py
    """
    
    CHUNK_SIZE = 500  # 每块约500字
    CHUNK_OVERLAP = 50
    
    async def upload_document(self, user_id, file, filename):
        # 1. 解析文档
        text = await self._parse_document(file, filename)
        
        # 2. 分块
        chunks = self._split_into_chunks(text)
        
        # 3. 保存文档记录
        doc_id = await self._save_document(user_id, filename, len(chunks))
        
        # 4. 异步向量化（提交到arq worker）
        await arq_pool.enqueue_job('vectorize_document', doc_id, chunks, user_id)
        
        return doc_id
    
    async def search(self, user_id, query, top_k=5):
        """语义搜索用户知识库"""
        # 1. 查询向量化
        query_embedding = await get_embedding(query)
        
        # 2. FAISS搜索
        results = await faiss_cache.search_user_knowledge(
            user_id, query_embedding, top_k
        )
        
        return results
    
    def _parse_document(self, file, filename):
        """支持PDF/Word/Markdown/TXT/URL"""
        ext = filename.rsplit('.', 1)[-1].lower()
        if ext == 'pdf':
            import pymupdf
            # PDF解析
        elif ext == 'docx':
            import docx
            # Word解析
        elif ext in ('md', 'txt'):
            return file.read().decode('utf-8')
        # URL解析...
```

### 3.3 团队服务

```python
class TeamService:
    """
    团队协作服务
    
    核心逻辑:
    - 团队创建时自动将创建者设为owner
    - 邀请链接24小时有效
    - 审批流程: submitted → approved/rejected
    - 团队风格覆盖个人风格（团队优先）
    """
    
    async def create_team(self, owner_id, name, description=None):
        team = await self._create_team_record(owner_id, name, description)
        await self._add_member(team.id, owner_id, 'owner')
        return team
    
    async def submit_for_review(self, article_id, user_id):
        team = await self._get_user_team(user_id)
        member = await self._get_member(team.id, user_id)
        
        if member.role not in ('editor',):
            raise PermissionError("Only editors need to submit for review")
        
        await self._create_approval(article_id, team.id, user_id)
        # 通知Admin/Owner
        await notification_service.notify_team_admins(
            team.id, f"新文章待审批: {article.title}"
        )
```

---

## 四、article_worker RAG集成

在文章生成时，如果用户启用了知识库，先检索再生成：

```python
# article_worker.py 修改点

async def generate_article_task(ctx, task_id, topic, user_id, ...):
    # ... 现有逻辑 ...
    
    # === P2新增: 知识库RAG ===
    kb_context = ""
    if await _is_knowledge_base_enabled(user_id):
        from backend.api.services.knowledge_base import KnowledgeBaseService
        kb_service = KnowledgeBaseService()
        results = await kb_service.search(user_id, topic, top_k=5)
        if results:
            kb_context = "\n\n## 参考知识库内容\n"
            for r in results:
                kb_context += f"- {r['content'][:200]}...\n"
    
    # 将kb_context注入到生成prompt中
    # custom_style += kb_context
```

---

## 五、定时任务扩展

P2 新增定时任务：

| 任务 | 频率 | 说明 |
|------|------|------|
| `publish_scheduled_job` | 每分钟 | 检查并执行定时发布任务 |
| `invitation_expire_job` | 每小时 | 清理过期的团队邀请 |
| `token_refresh_job` | 每小时 | 刷新即将过期的平台OAuth token |

---

## 六、第三方依赖

| 依赖 | 用途 | 版本 |
|------|------|------|
| `pymupdf` | PDF文档解析 | ≥1.23 |
| `python-docx` | Word文档解析 | ≥0.8 |
| `wechatpy` | 微信公众号API SDK | ≥2.x |
| `@fullcalendar/react` | 前端日历组件 | ≥6.x |

---

## 七、权限控制扩展

P2 引入团队维度的权限控制：

```python
# 团队权限中间件
async def require_team_role(min_role: str):
    """检查用户在团队中的角色"""
    async def dependency(
        current_user_id: int = Depends(get_current_user),
        team_id: int = Path(...)
    ):
        member = await team_service.get_member(team_id, current_user_id)
        if not member:
            raise HTTPException(403, "Not a team member")
        
        ROLE_LEVELS = {'viewer': 0, 'editor': 1, 'admin': 2, 'owner': 3}
        if ROLE_LEVELS[member.role] < ROLE_LEVELS[min_role]:
            raise HTTPException(403, f"Requires {min_role} role")
        
        return current_user_id
    return dependency
```

---

## 八、测试要点

| 功能 | 测试类型 | 关键用例 |
|------|---------|---------|
| F13 发布 | 集成 | OAuth绑定→格式转换→API发布→结果验证 |
| F14 知识库 | 集成+性能 | 文档解析→向量化→检索准确性→RAG生成质量 |
| F15 团队 | 集成+权限 | 创建→邀请→角色权限→审批流程→品牌风格 |
| F16 日历 | E2E | 日历展示→拖拽排期→节日提醒→定时发布 |
| F17 API | 集成+安全 | API Key认证→调用→计量→限流→文档 |

---

*本文档配合 P2 PRD 和 Sprint 计划使用*
