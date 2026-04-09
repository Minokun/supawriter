# P1 技术设计文档 — 付费价值构建

> **创建日期**: 2026-02-15
> **版本**: v1.0
> **关联PRD**: `docs/plans/2026-02-15-p1-prd.md`
> **关联总纲**: `docs/plans/2026-02-15-development-master-plan.md`
> **前置**: P0 全部功能已上线

---

## 一、架构总览

### 1.1 P1 功能在系统中的位置

```
┌─────────────────── Frontend (Next.js) ───────────────────┐
│                                                          │
│  写作页(扩展)    批量生成页(新)   Agent页(新)   看板页(新)  │
│  ┌──────┐      ┌──────┐       ┌──────┐     ┌──────┐    │
│  │F7:   │      │F8:   │       │F9:   │     │F11:  │    │
│  │SEO   │      │批量   │       │Agent │     │数据   │    │
│  │面板   │      │生成   │       │管理  │     │看板   │    │
│  └──────┘      └──────┘       └──────┘     └──────┘    │
│                                                          │
│  通知中心(新)          定价页(新)         设置页(扩展)      │
│  ┌──────┐            ┌──────┐          ┌──────┐        │
│  │F10:  │            │F12:  │          │订阅   │        │
│  │预警   │            │定价   │          │管理   │        │
│  │通知   │            │支付   │          │配额   │        │
│  └──────┘            └──────┘          └──────┘        │
└──────────────────────────────────────────────────────────┘
                          │
                    API Layer
                          │
┌─────────────────── Backend (FastAPI) ────────────────────┐
│                                                          │
│  routes/                                                 │
│  ├── seo.py              (新增: SEO分析API)              │
│  ├── batch.py            (新增: 批量生成API)             │
│  ├── agents.py           (新增: 写作Agent CRUD+调度)     │
│  ├── notifications.py    (新增: 通知API)                 │
│  ├── analytics.py        (新增: 数据看板API)             │
│  ├── pricing.py          (新增: 定价+订阅API)            │
│  └── payments.py         (新增: 支付回调API)             │
│                                                          │
│  services/                                               │
│  ├── seo_analyzer.py     (新增: SEO分析引擎)             │
│  ├── batch_service.py    (新增: 批量任务编排)             │
│  ├── agent_scheduler.py  (新增: Agent调度器)             │
│  ├── alert_service.py    (新增: 热点预警匹配)            │
│  ├── analytics_service.py(新增: 数据统计聚合)            │
│  └── payment_service.py  (新增: 支付+订阅管理)           │
│                                                          │
│  workers/                                                │
│  ├── article_worker.py   (已有，批量生成复用)             │
│  ├── agent_worker.py     (新增: Agent定时任务)           │
│  └── alert_worker.py     (新增: 热点扫描定时任务)        │
└──────────────────────────────────────────────────────────┘
```

### 1.2 新增/修改文件清单

| 类型 | 文件路径 | 操作 | 说明 |
|------|---------|------|------|
| **后端-路由** | `backend/api/routes/seo.py` | 新增 | SEO分析API |
| **后端-路由** | `backend/api/routes/batch.py` | 新增 | 批量生成API |
| **后端-路由** | `backend/api/routes/agents.py` | 新增 | Agent CRUD API |
| **后端-路由** | `backend/api/routes/notifications.py` | 新增 | 通知中心API |
| **后端-路由** | `backend/api/routes/analytics.py` | 新增 | 数据看板API |
| **后端-路由** | `backend/api/routes/pricing.py` | 新增 | 定价+订阅API |
| **后端-路由** | `backend/api/routes/payments.py` | 新增 | 支付回调API |
| **后端-服务** | `backend/api/services/seo_analyzer.py` | 新增 | SEO分析引擎 |
| **后端-服务** | `backend/api/services/batch_service.py` | 新增 | 批量任务编排 |
| **后端-服务** | `backend/api/services/agent_scheduler.py` | 新增 | Agent调度 |
| **后端-服务** | `backend/api/services/alert_service.py` | 新增 | 热点预警 |
| **后端-服务** | `backend/api/services/analytics_service.py` | 新增 | 数据统计 |
| **后端-服务** | `backend/api/services/payment_service.py` | 新增 | 支付管理 |
| **后端-Worker** | `backend/api/workers/agent_worker.py` | 新增 | Agent定时任务 |
| **后端-Worker** | `backend/api/workers/alert_worker.py` | 新增 | 热点扫描 |
| **后端-主入口** | `backend/api/main.py` | 修改 | 注册7个新路由 |
| **前端-页面** | `frontend/src/app/batch/page.tsx` | 新增 | 批量生成页 |
| **前端-页面** | `frontend/src/app/agents/page.tsx` | 新增 | Agent管理页 |
| **前端-页面** | `frontend/src/app/analytics/page.tsx` | 新增 | 数据看板页 |
| **前端-页面** | `frontend/src/app/pricing/page.tsx` | 新增 | 定价页 |
| **前端-组件** | `frontend/src/components/seo/SEOPanel.tsx` | 新增 | SEO分析面板 |
| **前端-组件** | `frontend/src/components/notifications/NotificationCenter.tsx` | 新增 | 通知中心 |
| **前端-组件** | `frontend/src/components/analytics/` | 新增 | 图表组件集 |
| **数据库** | `deployment/migrate/009_p1_features.sql` | 新增 | P1数据库迁移 |

---

## 二、数据库变更

### 2.1 新增表

#### batch_tasks — 批量任务

```sql
CREATE TABLE IF NOT EXISTS batch_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    total_count INTEGER NOT NULL,
    completed_count INTEGER DEFAULT 0,
    failed_count INTEGER DEFAULT 0,
    status VARCHAR(20) NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'running', 'completed', 'partial', 'cancelled')),
    settings JSONB NOT NULL DEFAULT '{}',
    -- settings: { model_type, model_name, word_count, search_depth, style_active }
    topics TEXT[] NOT NULL,
    article_ids INTEGER[] DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_batch_tasks_user_id ON batch_tasks(user_id);
CREATE INDEX idx_batch_tasks_status ON batch_tasks(status);
```

#### writing_agents — 写作Agent

```sql
CREATE TABLE IF NOT EXISTS writing_agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    domain_keywords TEXT[] NOT NULL DEFAULT '{}',
    frequency VARCHAR(50) NOT NULL DEFAULT 'daily',
        -- 'daily', 'three_per_week', 'weekly', 自定义cron表达式
    target_platform VARCHAR(20) DEFAULT 'wechat',
    model_type VARCHAR(50) DEFAULT 'deepseek',
    model_name VARCHAR(100) DEFAULT 'deepseek-chat',
    style_active BOOLEAN DEFAULT TRUE,
    is_active BOOLEAN DEFAULT TRUE,
    total_generated INTEGER DEFAULT 0,
    last_run_at TIMESTAMPTZ,
    next_run_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_writing_agents_user_id ON writing_agents(user_id);
CREATE INDEX idx_writing_agents_next_run ON writing_agents(next_run_at) WHERE is_active = TRUE;
```

#### agent_drafts — Agent草稿

```sql
CREATE TABLE IF NOT EXISTS agent_drafts (
    id SERIAL PRIMARY KEY,
    agent_id UUID NOT NULL REFERENCES writing_agents(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    article_id INTEGER REFERENCES articles(id) ON DELETE SET NULL,
    topic VARCHAR(500) NOT NULL,
    hotspot_source VARCHAR(50),
    score INTEGER,
    status VARCHAR(20) DEFAULT 'draft'
        CHECK (status IN ('draft', 'published', 'discarded')),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_agent_drafts_agent_id ON agent_drafts(agent_id);
CREATE INDEX idx_agent_drafts_user_id ON agent_drafts(user_id);
```

#### user_alert_configs — 预警配置

```sql
CREATE TABLE IF NOT EXISTS user_alert_configs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    keywords TEXT[] NOT NULL DEFAULT '{}',
    sources TEXT[] DEFAULT '{baidu,weibo,douyin,thepaper,36kr}',
    frequency VARCHAR(20) DEFAULT 'realtime'
        CHECK (frequency IN ('realtime', 'hourly', 'daily')),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_user_alert_config UNIQUE (user_id)
);
```

#### notifications — 通知

```sql
CREATE TABLE IF NOT EXISTS notifications (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type VARCHAR(50) NOT NULL,
        -- 'hotspot_alert', 'agent_complete', 'quota_warning', 'subscription_expiry'
    title VARCHAR(200) NOT NULL,
    content TEXT,
    metadata JSONB DEFAULT '{}',
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_notifications_user_id ON notifications(user_id);
CREATE INDEX idx_notifications_unread ON notifications(user_id, is_read) WHERE is_read = FALSE;
```

#### orders — 订单

```sql
CREATE TABLE IF NOT EXISTS orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    order_type VARCHAR(20) NOT NULL CHECK (order_type IN ('subscription', 'quota_pack')),
    plan VARCHAR(20), -- 'pro', 'ultra'
    period VARCHAR(20), -- 'monthly', 'yearly'
    amount_cents INTEGER NOT NULL, -- 金额（分）
    status VARCHAR(20) NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'paid', 'failed', 'refunded', 'cancelled')),
    payment_method VARCHAR(20), -- 'wechat', 'alipay'
    payment_id VARCHAR(100), -- 第三方支付订单号
    paid_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ -- 订单过期时间（30分钟未支付自动取消）
);

CREATE INDEX idx_orders_user_id ON orders(user_id);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_payment_id ON orders(payment_id);
```

#### subscriptions — 订阅

```sql
CREATE TABLE IF NOT EXISTS subscriptions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    plan VARCHAR(20) NOT NULL CHECK (plan IN ('pro', 'ultra')),
    period VARCHAR(20) NOT NULL CHECK (period IN ('monthly', 'yearly')),
    status VARCHAR(20) NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'cancelled', 'expired')),
    current_period_start TIMESTAMPTZ NOT NULL,
    current_period_end TIMESTAMPTZ NOT NULL,
    auto_renew BOOLEAN DEFAULT TRUE,
    cancelled_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_user_subscription UNIQUE (user_id)
);

CREATE INDEX idx_subscriptions_user_id ON subscriptions(user_id);
CREATE INDEX idx_subscriptions_expiry ON subscriptions(current_period_end) WHERE status = 'active';
```

#### quota_packs — 额度包

```sql
CREATE TABLE IF NOT EXISTS quota_packs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    pack_type VARCHAR(20) NOT NULL, -- 'pack_10', 'pack_50'
    total_quota INTEGER NOT NULL,
    used_quota INTEGER DEFAULT 0,
    order_id UUID REFERENCES orders(id),
    purchased_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ -- 额度包有效期（购买后1年）
);

CREATE INDEX idx_quota_packs_user_id ON quota_packs(user_id);
```

#### platform_convert_logs — 平台转换日志（用于数据看板统计）

```sql
CREATE TABLE IF NOT EXISTS platform_convert_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    article_id INTEGER,
    platform VARCHAR(20) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_convert_logs_user_date ON platform_convert_logs(user_id, created_at);
```

---

## 三、API 接口设计

### 3.1 SEO分析 API

```
POST /api/v1/articles/{article_id}/seo-analyze
Authorization: Bearer {token}
Tier: Pro+

Response:
{
    "keywords": [
        { "word": "AI写作", "count": 8, "density": 2.1, "status": "good" },
        { "word": "内容营销", "count": 3, "density": 0.8, "status": "low" }
    ],
    "title_score": 65,
    "title_suggestions": [
        "AI写作工具如何提升内容营销效率？",
        "2026年最佳AI写作工具：提升SEO排名指南"
    ],
    "meta_description": "本文介绍了AI写作工具在内容营销中的应用...",
    "internal_links": [
        { "anchor": "内容营销策略", "target_article_id": 45, "target_title": "2026内容营销趋势" }
    ],
    "long_tail_keywords": ["AI写作工具推荐", "内容营销自动化"]
}
```

### 3.2 批量生成 API

```
POST /api/v1/batch/create
Authorization: Bearer {token}
Tier: Ultra

Request:
{
    "topics": ["AI写作工具评测", "内容营销策略2026", "SEO优化入门"],
    "settings": {
        "model_type": "deepseek",
        "model_name": "deepseek-chat",
        "word_count_range": [2000, 3000],
        "search_depth": "standard",
        "style_active": true
    }
}

Response:
{
    "batch_id": "uuid",
    "total_count": 3,
    "estimated_minutes": 10
}

---

GET /api/v1/batch/{batch_id}/status

Response:
{
    "batch_id": "uuid",
    "status": "running",
    "total": 3,
    "completed": 1,
    "failed": 0,
    "items": [
        { "index": 0, "topic": "AI写作工具评测", "status": "completed", "article_id": 123 },
        { "index": 1, "topic": "内容营销策略2026", "status": "running", "progress": 60 },
        { "index": 2, "topic": "SEO优化入门", "status": "queued" }
    ]
}
```

### 3.3 写作Agent API

```
POST /api/v1/agents/create
Request:
{
    "name": "科技热点追踪",
    "domain_keywords": ["AI", "科技", "创业"],
    "frequency": "daily",
    "target_platform": "wechat",
    "model_type": "deepseek",
    "model_name": "deepseek-chat"
}

GET /api/v1/agents/list
Response: { "agents": [...], "max_agents": 3 }

PUT /api/v1/agents/{agent_id}
POST /api/v1/agents/{agent_id}/pause
POST /api/v1/agents/{agent_id}/resume
DELETE /api/v1/agents/{agent_id}

GET /api/v1/agents/{agent_id}/drafts?page=1&limit=20
Response: { "drafts": [...], "total": 12 }
```

### 3.4 通知 API

```
GET /api/v1/notifications?type=hotspot_alert&unread_only=true&limit=20
Response: {
    "notifications": [
        {
            "id": 1,
            "type": "hotspot_alert",
            "title": "热点预警: OpenAI发布GPT-5",
            "content": "百度热搜出现与您关注的\"AI\"相关的热点",
            "metadata": { "hotspot_title": "...", "source": "baidu", "keyword": "AI" },
            "is_read": false,
            "created_at": "2026-02-15T10:00:00Z"
        }
    ],
    "unread_count": 3
}

POST /api/v1/notifications/{id}/read
POST /api/v1/notifications/read-all
```

### 3.5 数据看板 API

```
GET /api/v1/analytics/dashboard?period=month
Response: {
    "overview": {
        "article_count": 28,
        "article_count_change": 0.12,
        "total_words": 82000,
        "avg_score": 81,
        "avg_score_change": 9,
        "hotspot_hit_rate": 0.35
    },
    "score_trend": [
        { "date": "2026-02-01", "avg_score": 72, "count": 3 },
        { "date": "2026-02-02", "avg_score": 78, "count": 2 }
    ],
    "topic_distribution": [
        { "topic": "科技", "count": 12 },
        { "topic": "营销", "count": 8 }
    ],
    "platform_usage": [
        { "platform": "wechat", "count": 45 },
        { "platform": "zhihu", "count": 20 }
    ]
}
```

### 3.6 支付 API

```
GET /api/v1/pricing/plans
Response: {
    "plans": [
        { "id": "pro", "name": "Pro", "monthly_price": 4900, "yearly_price": 46800, ... },
        { "id": "ultra", "name": "Ultra", "monthly_price": 9900, "yearly_price": 94800, ... }
    ],
    "quota_packs": [
        { "id": "pack_10", "quota": 10, "price": 1990 },
        { "id": "pack_50", "quota": 50, "price": 7990 }
    ]
}

POST /api/v1/orders/create
Request: { "plan": "pro", "period": "monthly", "payment_method": "wechat" }
Response: { "order_id": "uuid", "payment_url": "weixin://...", "qr_code_url": "https://..." }

POST /api/v1/payments/wechat/callback  (微信支付回调，无需认证)
Request: XML格式的微信回调数据

GET /api/v1/user/subscription
Response: {
    "plan": "pro",
    "status": "active",
    "period_end": "2026-03-15T00:00:00Z",
    "auto_renew": true,
    "quota": { "monthly_total": 30, "monthly_used": 12, "pack_remaining": 0 }
}
```

---

## 四、核心服务设计

### 4.1 SEO分析引擎

```python
class SEOAnalyzer:
    """
    SEO分析引擎
    
    混合策略:
    - 关键词提取+密度计算: jieba分词 (纯规则，快速)
    - 标题优化+元描述: LLM生成 (需要创意)
    - 内链建议: 数据库查询 (用户历史文章匹配)
    """
    
    def __init__(self):
        import jieba
        self.jieba = jieba
    
    async def analyze(self, content: str, title: str, user_id: int) -> SEOReport:
        # 并行执行三个分析
        keywords = self._extract_keywords(content)
        title_result = await self._analyze_title(title, keywords)
        internal_links = await self._find_internal_links(content, user_id)
        
        return SEOReport(
            keywords=keywords,
            title_score=title_result.score,
            title_suggestions=title_result.suggestions,
            meta_description=title_result.meta_description,
            internal_links=internal_links,
            long_tail_keywords=title_result.long_tail
        )
    
    def _extract_keywords(self, content: str) -> list:
        """jieba分词 + TF-IDF提取关键词"""
        import jieba.analyse
        keywords = jieba.analyse.extract_tags(content, topK=5, withWeight=True)
        total_chars = len(content)
        result = []
        for word, weight in keywords:
            count = content.count(word)
            density = round(count * len(word) / total_chars * 100, 1)
            status = "good" if 1.5 <= density <= 3.5 else ("high" if density > 3.5 else "low")
            result.append({"word": word, "count": count, "density": density, "status": status})
        return result
```

### 4.2 批量任务编排

```python
class BatchService:
    """
    批量生成编排器
    
    并发策略: 最多3个任务并行，使用asyncio.Semaphore控制
    失败策略: 单篇失败不影响其他，记录失败原因，支持单独重试
    """
    
    MAX_CONCURRENT = 3
    
    async def create_batch(self, user_id: int, topics: list, settings: dict) -> str:
        # 1. 创建batch记录
        # 2. 将batch任务提交到arq
        batch_id = str(uuid.uuid4())
        await arq_pool.enqueue_job(
            'run_batch_task', batch_id, topics, settings, user_id
        )
        return batch_id
    
    async def run_batch(self, batch_id: str, topics: list, settings: dict, user_id: int):
        semaphore = asyncio.Semaphore(self.MAX_CONCURRENT)
        tasks = []
        for i, topic in enumerate(topics):
            task = self._generate_one(semaphore, batch_id, i, topic, settings, user_id)
            tasks.append(task)
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _generate_one(self, sem, batch_id, index, topic, settings, user_id):
        async with sem:
            # 复用现有 article_worker 的生成逻辑
            pass
```

### 4.3 Agent调度器

```python
class AgentScheduler:
    """
    写作Agent调度器
    
    运行方式: arq cron job，每5分钟检查一次是否有Agent需要执行
    """
    
    async def check_and_run(self):
        """定时检查需要执行的Agent"""
        now = datetime.utcnow()
        agents = await self._get_due_agents(now)
        for agent in agents:
            await self._run_agent(agent)
    
    async def _run_agent(self, agent):
        """
        Agent执行流程:
        1. 获取热点数据
        2. LLM筛选与领域相关的话题
        3. 选择最佳话题
        4. 调用文章生成pipeline
        5. 自动评分
        6. 存入草稿箱
        7. 发送通知
        8. 更新next_run_at
        """
        # 1. 获取热点
        from backend.api.services.hotspots_service import HotspotsService
        hotspots = await HotspotsService().get_hotspots('baidu')
        
        # 2. LLM筛选
        relevant = await self._filter_by_domain(
            hotspots['data'], agent['domain_keywords']
        )
        
        if not relevant:
            logger.info(f"Agent {agent['id']}: no relevant hotspots found")
            return
        
        # 3. 选择最佳话题
        topic = relevant[0]['title']
        
        # 4. 生成文章（复用article_worker逻辑）
        # 5. 评分
        # 6. 存草稿
        # 7. 通知
        # 8. 更新调度时间
```

### 4.4 支付服务

```python
class PaymentService:
    """
    支付服务
    
    支付流程:
    1. 创建订单 → 调用微信支付API获取支付链接
    2. 用户扫码支付
    3. 微信回调 → 验证签名 → 更新订单状态 → 升级用户等级
    
    安全要求:
    - 回调必须验证微信签名
    - 订单金额必须与预期一致
    - 等级变更必须在事务中完成
    """
    
    async def create_order(self, user_id: int, plan: str, period: str, method: str) -> Order:
        amount = self._calculate_amount(plan, period)
        order = await self._save_order(user_id, plan, period, amount, method)
        
        if method == 'wechat':
            payment_url = await self._create_wechat_payment(order)
            return {"order_id": order.id, "payment_url": payment_url}
    
    async def handle_wechat_callback(self, data: dict) -> bool:
        # 1. 验证签名
        if not self._verify_wechat_sign(data):
            raise SecurityError("Invalid signature")
        
        # 2. 查找订单
        order = await self._get_order_by_payment_id(data['out_trade_no'])
        
        # 3. 验证金额
        if order.amount_cents != int(data['total_fee']):
            raise SecurityError("Amount mismatch")
        
        # 4. 事务: 更新订单 + 创建/更新订阅 + 变更用户等级
        async with db.transaction():
            await self._mark_order_paid(order)
            await self._create_subscription(order)
            await self._upgrade_user_tier(order.user_id, order.plan)
        
        return True
```

---

## 五、定时任务设计

P1 引入两个定时任务，均基于 arq cron：

| 任务 | 频率 | 说明 |
|------|------|------|
| `agent_check_job` | 每5分钟 | 检查是否有Agent需要执行 |
| `alert_scan_job` | 每5分钟 | 扫描热点匹配用户关注词 |
| `subscription_check_job` | 每小时 | 检查即将到期的订阅，发送提醒 |
| `order_expire_job` | 每10分钟 | 取消超时未支付的订单 |

在 arq worker 配置中注册：

```python
# backend/api/workers/worker_settings.py
class WorkerSettings:
    cron_jobs = [
        cron(agent_check_job, minute={0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55}),
        cron(alert_scan_job, minute={2, 7, 12, 17, 22, 27, 32, 37, 42, 47, 52, 57}),
        cron(subscription_check_job, minute=0),
        cron(order_expire_job, minute={0, 10, 20, 30, 40, 50}),
    ]
```

---

## 六、前端组件设计

### 6.1 SEOPanel 组件

```typescript
// frontend/src/components/seo/SEOPanel.tsx
// 侧边栏/底部展开面板
// 模块: 关键词分析 | 标题优化 | 元描述 | 内链建议
// 关键词密度用颜色标注: green(good) / yellow(low) / red(high)
// 标题建议可一键应用（替换当前标题）
```

### 6.2 BatchProgress 组件

```typescript
// frontend/src/app/batch/page.tsx
// 左侧: 主题输入区 + 统一设置
// 右侧: 进度展示（总进度条 + 每篇状态列表）
// 状态轮询: 每3秒调用 GET /batch/{id}/status
// 完成后: 批量下载按钮（ZIP）
```

### 6.3 AgentManager 组件

```typescript
// frontend/src/app/agents/page.tsx
// Agent卡片列表 + 创建Agent弹窗
// 每个卡片: 状态指示灯 + 配置摘要 + 统计 + 操作按钮
// 草稿箱: 点击Agent卡片展开草稿列表
```

### 6.4 NotificationCenter 组件

```typescript
// frontend/src/components/notifications/NotificationCenter.tsx
// 导航栏右侧铃铛图标 + 未读数badge
// 点击展开下拉面板
// 热点预警通知带"写这个"快捷按钮
// WebSocket实时推送新通知
```

### 6.5 Analytics Dashboard

```typescript
// frontend/src/app/analytics/page.tsx
// 图表库: recharts (已在Next.js生态中广泛使用)
// 顶部: 4个数字卡片（文章数/字数/评分/命中率）
// 中部: 评分趋势折线图 + 领域分布词云
// 底部: 热点来源饼图 + 平台使用柱状图
// 时间筛选: 本周/本月/全部
```

### 6.6 PricingPage

```typescript
// frontend/src/app/pricing/page.tsx
// 三列对比卡片布局
// Pro卡片加"最受欢迎"标签
// 月付/年付切换（年付显示折扣百分比）
// 支付弹窗: 显示微信支付二维码
// 支付状态轮询: 每2秒检查订单状态
```

---

## 七、权限控制矩阵

| API/功能 | Free | Pro | Ultra |
|---------|------|-----|-------|
| SEO分析 | 🔒 | ✅ | ✅ |
| 批量生成 | 🔒 | 🔒 | ✅ |
| 写作Agent | 🔒 | 🔒 | ✅ (最多3个) |
| 热点预警 | 🔒 | ✅ (5关键词) | ✅ (10关键词) |
| 数据看板 | 🔒 | ✅ | ✅ |
| 去水印 | ❌ | ✅ | ✅ |

权限检查统一通过中间件 + `TierService` 实现：

```python
# 权限装饰器
def require_tier(min_tier: str):
    async def dependency(current_user_id: int = Depends(get_current_user)):
        tier = await TierService.get_user_tier(current_user_id)
        if TierService.TIER_LEVELS[tier] < TierService.TIER_LEVELS[min_tier]:
            raise HTTPException(403, f"此功能需要{min_tier}及以上等级")
        return current_user_id
    return dependency
```

---

## 八、第三方依赖

| 依赖 | 用途 | 版本 |
|------|------|------|
| `jieba` | 中文分词（SEO关键词提取） | ≥0.42 |
| `wechatpayv3` | 微信支付V3 SDK | 最新 |
| `recharts` | 前端图表（数据看板） | ≥2.x |
| `apscheduler` | 定时任务（备选，如arq cron不够用） | ≥3.10 |

---

## 九、测试要点

| 功能 | 测试类型 | 关键用例 |
|------|---------|---------|
| F7 SEO | 单元+集成 | 关键词提取准确性、密度计算、标题优化质量 |
| F8 批量 | 集成+压力 | 并发控制、单篇失败不影响整体、20篇批量 |
| F9 Agent | 集成+定时 | 定时触发、热点筛选、草稿生成、通知推送 |
| F10 预警 | 集成 | 关键词匹配、WebSocket推送、通知→写这个链路 |
| F11 看板 | 单元+集成 | 统计数据准确性、大数据量下查询性能 |
| F12 支付 | 集成+安全 | 支付流程完整性、回调签名验证、并发防重、配额原子性 |

---

*本文档配合 P1 PRD 和 Sprint 计划使用*
