# Sprint 7 设计文档：批量生成 + 写作Agent

> 创建日期: 2026-02-20
> 目标: 实现 F8 批量生成 和 F9 写作Agent

---

## 1. 功能概述

### F8 批量生成 (Batch Generation)
允许用户一次性提交多个主题，系统自动并发生成文章，支持进度追踪和批量导出。

**核心价值**: 提升内容生产效率，适合定期内容规划

### F9 写作Agent (Writing Agent)
智能代理系统自动监控热点，根据用户预设规则自动生成文章草稿。

**核心价值**: 自动化内容创作，抢占热点先机

---

## 2. 数据模型设计

### 2.1 批量生成相关

```python
# backend/api/db/models/batch.py

class BatchJob(Base):
    """批量生成任务主表"""
    __tablename__ = 'batch_jobs'

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'))

    # 任务配置
    name: Mapped[str] = mapped_column(String(200))  # 任务名称
    topics: Mapped[list] = mapped_column(JSONB)  # ["主题1", "主题2", ...]
    platform: Mapped[str] = mapped_column(String(50))  # wechat/zhihu/xiaohongshu
    style_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey('user_styles.id'), nullable=True)

    # 状态追踪
    status: Mapped[str] = mapped_column(String(20))  # pending/running/completed/failed/partial
    total_count: Mapped[int] = mapped_column(Integer, default=0)
    completed_count: Mapped[int] = mapped_column(Integer, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, default=0)

    # 配置选项
    concurrency: Mapped[int] = mapped_column(Integer, default=3)  # 并发数
    generate_images: Mapped[bool] = mapped_column(Boolean, default=False)

    # 结果
    zip_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    tasks: Mapped[list["BatchTask"]] = relationship("BatchTask", back_populates="job", cascade="all, delete-orphan")


class BatchTask(Base):
    """批量生成子任务表"""
    __tablename__ = 'batch_tasks'

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    job_id: Mapped[UUID] = mapped_column(ForeignKey('batch_jobs.id', ondelete='CASCADE'))

    # 任务内容
    topic: Mapped[str] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(20))  # pending/running/completed/failed

    # 结果
    article_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey('articles.id'), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 时间追踪
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    job: Mapped["BatchJob"] = relationship("BatchJob", back_populates="tasks")
    article: Mapped[Optional["Article"]] = relationship("Article")
```

### 2.2 写作Agent相关

```python
# backend/api/db/models/agent.py

class WritingAgent(Base):
    """写作Agent配置表"""
    __tablename__ = 'writing_agents'

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'))

    # 基础配置
    name: Mapped[str] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # 触发规则 (JSON配置)
    trigger_rules: Mapped[dict] = mapped_column(JSONB)  # 见下方结构

    # 生成配置
    platform: Mapped[str] = mapped_column(String(50))  # 默认输出平台
    style_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey('user_styles.id'), nullable=True)
    generate_images: Mapped[bool] = mapped_column(Boolean, default=False)

    # 限制配置
    max_daily: Mapped[int] = mapped_column(Integer, default=5)  # 每日最大生成数
    min_hot_score: Mapped[int] = mapped_column(Integer, default=70)  # 最小热度分

    # 统计
    total_triggered: Mapped[int] = mapped_column(Integer, default=0)
    today_triggered: Mapped[int] = mapped_column(Integer, default=0)
    last_triggered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    # Relationships
    drafts: Mapped[list["AgentDraft"]] = relationship("AgentDraft", back_populates="agent")


# trigger_rules JSON结构示例:
# {
#     "sources": ["baidu", "weibo", "zhihu"],  # 监控的热点源
#     "keywords": ["人工智能", "AI"],  # 关键词匹配（可选）
#     "categories": ["tech", "finance"],  # 分类筛选
#     "exclude_keywords": ["广告", "推广"],  # 排除词
#     "min_heat": 100000,  # 最小热度值
# }


class AgentDraft(Base):
    """Agent生成的草稿表"""
    __tablename__ = 'agent_drafts'

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    agent_id: Mapped[UUID] = mapped_column(ForeignKey('writing_agents.id', ondelete='CASCADE'))
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'))

    # 来源信息
    hotspot_title: Mapped[str] = mapped_column(String(500))
    hotspot_source: Mapped[str] = mapped_column(String(50))
    hotspot_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    hotspot_heat: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # 生成的文章
    article_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey('articles.id'), nullable=True)

    # 状态
    status: Mapped[str] = mapped_column(String(20))  # pending/generating/completed/reviewed/discarded

    # 用户操作
    user_rating: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 1-5星评分
    user_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 时间
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    agent: Mapped["WritingAgent"] = relationship("WritingAgent", back_populates="drafts")
    article: Mapped[Optional["Article"]] = relationship("Article")
```

---

## 3. 后端服务设计

### 3.1 批量生成服务

```python
# backend/api/services/batch_service.py

class BatchService:
    """批量生成服务"""

    async def create_batch_job(
        self,
        user_id: int,
        name: str,
        topics: List[str],
        platform: str,
        style_id: Optional[UUID] = None,
        concurrency: int = 3,
        generate_images: bool = False
    ) -> BatchJob:
        """创建批量生成任务"""

    async def start_batch_job(self, job_id: UUID) -> None:
        """启动批量任务（提交ARQ任务）"""

    async def get_job_status(self, job_id: UUID) -> Dict[str, Any]:
        """获取任务状态（包含进度）"""

    async def retry_failed_tasks(self, job_id: UUID) -> int:
        """重试失败的任务，返回重试数量"""

    async def generate_zip(self, job_id: UUID) -> str:
        """生成ZIP文件，返回下载URL"""

    async def cancel_job(self, job_id: UUID) -> bool:
        """取消进行中的任务"""
```

### 3.2 批量生成Worker

```python
# backend/api/workers/batch_worker.py

async def process_batch_job(ctx, job_id: UUID) -> Dict[str, Any]:
    """
    ARQ任务：处理批量生成任务

    1. 获取任务配置
    2. 创建子任务（每个主题一个）
    3. 并发执行（使用asyncio.Semaphore控制并发）
    4. 更新进度
    5. 生成ZIP（如果全部完成）
    """

async def generate_single_article(
    ctx,
    task_id: UUID,
    topic: str,
    platform: str,
    style_id: Optional[UUID],
    generate_images: bool
) -> Dict[str, Any]:
    """
    生成单篇文章

    复用现有的 article_worker 逻辑
    """
```

### 3.3 Agent服务

```python
# backend/api/services/agent_service.py

class AgentService:
    """写作Agent服务"""

    async def create_agent(
        self,
        user_id: int,
        name: str,
        trigger_rules: Dict[str, Any],
        platform: str,
        **config
    ) -> WritingAgent:
        """创建写作Agent"""

    async def evaluate_hotspot_for_agent(
        self,
        agent_id: UUID,
        hotspot: Dict[str, Any]
    ) -> bool:
        """评估热点是否匹配Agent规则"""

    async def generate_draft(
        self,
        agent_id: UUID,
        hotspot: Dict[str, Any]
    ) -> AgentDraft:
        """为匹配的热点生成草稿"""

    async def get_drafts_for_review(
        self,
        user_id: int,
        status: Optional[str] = None,
        page: int = 1,
        limit: int = 20
    ) -> List[AgentDraft]:
        """获取待审核的草稿列表"""
```

### 3.4 Agent Worker

```python
# backend/api/workers/agent_worker.py

async def scan_hotspots_for_agents(ctx) -> Dict[str, Any]:
    """
    ARQ定时任务：扫描热点并触发Agent

    执行频率: 每30分钟（与alert_worker同时执行）

    流程:
    1. 获取所有启用的Agent
    2. 获取热点数据
    3. 对每个Agent，筛选匹配的热点
    4. 检查每日生成限制
    5. 为匹配的热点生成草稿
    6. 发送通知（可选）
    """

async def generate_draft_for_hotspot(
    ctx,
    agent_id: UUID,
    hotspot: Dict[str, Any]
) -> Dict[str, Any]:
    """
    为特定热点生成草稿
    """
```

---

## 4. API 设计

### 4.1 批量生成API

```python
# POST /api/v1/batch/jobs
# 创建批量任务
{
    "name": "科技周报",
    "topics": ["AI发展", "新能源汽车", "区块链应用"],
    "platform": "wechat",
    "style_id": "uuid",
    "concurrency": 3,
    "generate_images": false
}

# GET /api/v1/batch/jobs/{job_id}
# 获取任务状态
{
    "id": "uuid",
    "name": "科技周报",
    "status": "running",
    "total_count": 10,
    "completed_count": 5,
    "failed_count": 0,
    "progress": 50,
    "tasks": [
        {"id": "uuid", "topic": "AI发展", "status": "completed", "article_id": "uuid"},
        {"id": "uuid", "topic": "新能源汽车", "status": "running"}
    ]
}

# POST /api/v1/batch/jobs/{job_id}/retry
# 重试失败任务

# POST /api/v1/batch/jobs/{job_id}/cancel
# 取消任务

# GET /api/v1/batch/jobs/{job_id}/download
# 下载ZIP文件
```

### 4.2 Agent API

```python
# POST /api/v1/agents
# 创建Agent
{
    "name": "科技热点追踪",
    "trigger_rules": {
        "sources": ["baidu", "weibo"],
        "keywords": ["AI", "人工智能"],
        "min_heat": 100000
    },
    "platform": "wechat",
    "style_id": "uuid",
    "max_daily": 5
}

# GET /api/v1/agents
# 获取Agent列表

# PUT /api/v1/agents/{agent_id}
# 更新Agent

# DELETE /api/v1/agents/{agent_id}
# 删除Agent

# GET /api/v1/agents/drafts
# 获取草稿列表
{
    "drafts": [
        {
            "id": "uuid",
            "agent_name": "科技热点追踪",
            "hotspot_title": "ChatGPT发布新功能",
            "hotspot_source": "weibo",
            "status": "completed",
            "created_at": "2026-02-20T10:00:00Z"
        }
    ]
}

# PUT /api/v1/agents/drafts/{draft_id}/review
# 审核草稿
{
    "action": "accept",  # accept/discard
    "rating": 4,
    "notes": "质量不错，稍作修改即可发布"
}

# POST /api/v1/agents/drafts/{draft_id}/publish
# 发布草稿（将文章状态改为已完成）
```

---

## 5. 前端设计

### 5.1 批量生成页面

```
/app/batch/page.tsx

功能模块:
1. 新建批量任务按钮 → 弹出Modal
   - 任务名称输入
   - 主题列表（支持批量粘贴，每行一个主题）
   - 平台选择
   - 风格选择
   - 并发数滑块（1-5）

2. 任务列表
   - 卡片展示每个任务
   - 进度条显示完成状态
   - 操作按钮：查看/重试/下载/删除

3. 任务详情Drawer
   - 每个主题的生成状态
   - 实时刷新进度
   - 失败原因显示
```

### 5.2 Agent管理页面

```
/app/agent/page.tsx

功能模块:
1. Agent列表
   - 开关控制启用状态
   - 今日生成数量/上限
   - 编辑/删除按钮

2. 新建/编辑Agent Modal
   - Agent名称
   - 监控热点源（多选）
   - 关键词匹配（标签输入）
   - 热度阈值滑块
   - 每日上限设置
   - 默认输出平台

3. 草稿箱Tab
   - 待审核草稿列表
   - 快速预览
   - 接受/丢弃按钮
```

### 5.3 新增API类型

```typescript
// frontend/src/types/api.ts

export interface BatchJob {
  id: string;
  name: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'partial';
  total_count: number;
  completed_count: number;
  failed_count: number;
  progress: number;
  zip_url?: string;
  created_at: string;
}

export interface BatchTask {
  id: string;
  topic: string;
  status: string;
  article_id?: string;
  error_message?: string;
}

export interface WritingAgent {
  id: string;
  name: string;
  is_active: boolean;
  trigger_rules: {
    sources: string[];
    keywords?: string[];
    min_heat?: number;
  };
  platform: string;
  max_daily: number;
  today_triggered: number;
  total_triggered: number;
}

export interface AgentDraft {
  id: string;
  agent_name: string;
  hotspot_title: string;
  hotspot_source: string;
  hotspot_heat?: number;
  status: string;
  article_id?: string;
  created_at: string;
}

// API functions
export const batchApi = {
  createJob: (data: CreateBatchJobRequest) => Promise<BatchJob>;
  getJob: (id: string) => Promise<BatchJob>;
  getJobs: () => Promise<BatchJob[]>;
  retryJob: (id: string) => Promise<void>;
  cancelJob: (id: string) => Promise<void>;
  downloadZip: (id: string) => Promise<Blob>;
};

export const agentApi = {
  createAgent: (data: CreateAgentRequest) => Promise<WritingAgent>;
  getAgents: () => Promise<WritingAgent[]>;
  updateAgent: (id: string, data: Partial<WritingAgent>) => Promise<WritingAgent>;
  deleteAgent: (id: string) => Promise<void>;
  getDrafts: (params?: {status?: string}) => Promise<AgentDraft[]>;
  reviewDraft: (id: string, action: 'accept' | 'discard') => Promise<void>;
};
```

---

## 6. 开发任务拆分

### Phase 1: 数据模型 (backend-dev)
- [ ] 创建 `backend/api/db/models/batch.py`
- [ ] 创建 `backend/api/db/models/agent.py`
- [ ] 更新 `__init__.py` 导出
- [ ] 生成数据库迁移

### Phase 2: 后端服务 (backend-dev)
- [ ] 实现 `batch_service.py`
- [ ] 实现 `agent_service.py`
- [ ] 实现 `batch_worker.py` (ARQ任务)
- [ ] 实现 `agent_worker.py` (ARQ任务)

### Phase 3: API接口 (backend-dev)
- [ ] 实现 `batch.py` API路由
- [ ] 实现 `agent.py` API路由
- [ ] 更新 `main.py` 注册路由

### Phase 4: 前端组件 (frontend-dev)
- [ ] 更新 `api.ts` 添加类型和API函数
- [ ] 创建 `/app/batch/page.tsx`
- [ ] 创建 `/app/agent/page.tsx`
- [ ] 添加导航入口

### Phase 5: 测试验证 (team-lead)
- [ ] 批量生成功能测试
- [ ] Agent触发测试
- [ ] 草稿箱流程测试

---

## 7. 技术要点

### 7.1 并发控制
```python
# 使用 Semaphore 控制并发
semaphore = asyncio.Semaphore(concurrency)

async def process_with_limit(task):
    async with semaphore:
        return await process_task(task)

# 并发执行
await asyncio.gather(*[process_with_limit(t) for t in tasks])
```

### 7.2 进度追踪
- 使用数据库字段实时更新进度
- 前端轮询获取最新状态（每5秒）
- 支持 WebSocket 实时推送（可选）

### 7.3 ZIP生成
```python
import zipfile
import io

async def create_zip(job_id: UUID) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for article in articles:
            content = await get_article_content(article.id)
            zf.writestr(f"{article.title}.md", content)
    return buffer.getvalue()
```

### 7.4 Agent触发时机
- 与热点预警共用扫描任务（30分钟）
- Agent草稿生成后发送通知
- 每日限制重置（凌晨0点）

---

## 8. 权限控制

| 功能 | Free | Pro | Ultra |
|------|------|-----|-------|
| 批量生成任务数/月 | 3 | 10 | 无限制 |
| 每批主题数 | 5 | 20 | 50 |
| 写作Agent数量 | 0 | 2 | 10 |
| Agent草稿保存天数 | - | 7天 | 30天 |

---

## 9. 风险评估

1. **并发控制不当导致系统负载过高**
   - 缓解：限制每用户并发数，使用队列

2. **Agent生成过多内容**
   - 缓解：每日生成上限，配额检查

3. **ZIP文件过大**
   - 缓解：限制批量大小，流式生成

---

*文档版本: 1.0*
*最后更新: 2026-02-20*
