# Sprint 6 设计文档：热点预警 + 数据看板

> **日期**: 2026-02-19
> **Sprint**: P1 Sprint 6
> **功能**: F10 热点预警 + F11 数据看板

---

## 架构概览

```
┌─────────────────────────────────────────────────────────────────┐
│                        Sprint 6 架构                             │
├─────────────────────────────────────────────────────────────────┤
│  前端                                                            │
│  ├── NotificationCenter 组件 (铃铛+下拉)                         │
│  ├── AlertSettings 页面 (关键词管理+AI推荐)                       │
│  └── Dashboard 页面 (按等级显示不同看板)                          │
├─────────────────────────────────────────────────────────────────┤
│  后端 API                                                        │
│  ├── /api/v1/alerts (预警CRUD)                                   │
│  ├── /api/v1/notifications (通知CRUD)                            │
│  └── /api/v1/dashboard (数据看板)                                │
├─────────────────────────────────────────────────────────────────┤
│  后端 Service                                                    │
│  ├── alert_service.py (热点匹配引擎)                              │
│  ├── notification_service.py (通知管理)                          │
│  └── analytics_service.py (统计聚合)                             │
├─────────────────────────────────────────────────────────────────┤
│  后台任务                                                        │
│  └── alert_worker.py (每30分钟扫描热点+匹配关键词)                │
└─────────────────────────────────────────────────────────────────┘
```

---

## 数据模型

### 1. AlertKeyword (用户关注关键词)
```python
class AlertKeyword(Base):
    __tablename__ = "alert_keywords"

    id: UUID (PK)
    user_id: UUID (FK -> users.id)
    keyword: str           # 关键词
    category: str          # 分类（可选）
    is_active: bool        # 是否启用
    created_at: datetime
```

### 2. AlertRecord (预警记录)
```python
class AlertRecord(Base):
    __tablename__ = "alert_records"

    id: UUID (PK)
    user_id: UUID (FK -> users.id)
    keyword_id: UUID (FK -> alert_keywords.id)
    hotspot_title: str     # 匹配的热点标题
    hotspot_source: str    # 热点来源 (baidu/weibo/etc)
    hotspot_url: str       # 热点链接
    matched_at: datetime   # 匹配时间
    is_read: bool          # 是否已读
```

### 3. UserStats (用户统计数据缓存)
```python
class UserStats(Base):
    __tablename__ = "user_stats"

    user_id: UUID (PK)
    total_articles: int      # 总创作数
    total_words: int         # 累计字数
    monthly_articles: int    # 本月生成数
    quota_used: int          # 已用配额
    quota_total: int         # 总配额
    avg_score: float         # 平均评分
    score_history: JSON      # 评分趋势 [{"date": "2026-02", "score": 72}]
    platform_stats: JSON     # 平台分布 {"wechat": 10, "zhihu": 5}
    # Ultra 专属
    hotspot_matches: int     # 热点匹配数
    keyword_hit_rate: float  # 关键词命中率
    model_usage: JSON        # 模型使用分布 {"deepseek": 20, "openai": 5}
    updated_at: datetime
```

---

## 后端服务

### 1. alert_service.py (热点预警服务)
```python
class AlertService:
    """热点预警匹配引擎"""

    async def add_keyword(user_id: UUID, keyword: str, category: str = None) -> AlertKeyword
    async def remove_keyword(keyword_id: UUID)
    async def get_user_keywords(user_id: UUID) -> List[AlertKeyword]
    async def toggle_keyword(keyword_id: UUID, is_active: bool)

    async def scan_and_match():
        """定时任务调用：扫描热点+匹配关键词"""
        # 1. 获取所有启用的关键词 (按用户分组)
        # 2. 获取各平台热点数据
        # 3. 匹配热点标题/内容
        # 4. 创建 AlertRecord
        # 5. 更新用户统计 (hotspot_matches)

    async def suggest_keywords(user_id: UUID) -> List[str]:
        """AI根据用户历史文章推荐关键词"""
        # 分析用户文章标题、主题，提取高频词
        # 调用 LLM 生成推荐关键词
```

### 2. notification_service.py (通知管理服务)
```python
class NotificationService:
    """通知管理"""

    async def get_unread_count(user_id: UUID) -> int
    async def get_notifications(user_id: UUID, page: int, limit: int) -> List[AlertRecord]
    async def mark_as_read(notification_id: UUID)
    async def mark_all_read(user_id: UUID)
    async def delete_notification(notification_id: UUID)
```

### 3. analytics_service.py (统计聚合服务)
```python
class AnalyticsService:
    """数据统计聚合"""

    async def get_user_stats(user_id: UUID, tier: str) -> UserStats:
        """获取用户统计数据（按等级返回不同字段）"""
        # Free: 基础统计
        # Pro: + 趋势图、平台分布
        # Ultra: + 热点匹配、关键词命中、模型使用

    async def refresh_user_stats(user_id: UUID):
        """刷新用户统计缓存（文章生成/评分后调用）"""

    async def refresh_all_stats():
        """每小时刷新所有用户统计"""
```

---

## API 端点

### 1. 预警关键词管理
```python
@router.get("/alerts/keywords")
# Response: {keywords: [{id, keyword, category, is_active, created_at}]}

@router.post("/alerts/keywords")
# Body: {keyword: str, category?: str}
# Response: {id, keyword, category, is_active}

@router.delete("/alerts/keywords/{keyword_id}")
# Response: {message: "deleted"}

@router.put("/alerts/keywords/{keyword_id}/toggle")
# Body: {is_active: bool}
# Response: {id, is_active}

@router.get("/alerts/suggest-keywords")
# Response: {keywords: [str]}  # AI推荐的关键词列表
```

### 2. 通知管理
```python
@router.get("/notifications")
# Query: ?page=1&limit=20
# Response: {notifications: [{id, keyword, hotspot_title, hotspot_source, matched_at, is_read}], total, unread_count}

@router.get("/notifications/unread-count")
# Response: {count: int}

@router.put("/notifications/{id}/read")
# Response: {id, is_read: true}

@router.put("/notifications/read-all")
# Response: {message: "all marked as read", count: int}

@router.delete("/notifications/{id}")
# Response: {message: "deleted"}
```

### 3. 数据看板
```python
@router.get("/dashboard")
# Response (Free): {
#   total_articles: int,
#   total_words: int,
#   monthly_articles: int,
#   quota_used: int,
#   quota_total: int
# }
# Response (Pro): + {
#   avg_score: float,
#   score_history: [{date, score}],
#   platform_stats: {wechat: int, zhihu: int, ...}
# }
# Response (Ultra): + {
#   hotspot_matches: int,
#   keyword_hit_rate: float,
#   model_usage: {deepseek: int, openai: int, ...}
# }
```

---

## 前端组件

### 1. NotificationCenter (通知中心)
```typescript
// 位置: 顶部导航栏右侧 (MainLayout)
// 图标: 铃铛 (lucide-react Bell)
// 红点: 未读数量 > 0 时显示

interface NotificationCenterProps {
  unreadCount: number;
  notifications: AlertRecord[];
  onMarkAsRead: (id: string) => void;
  onMarkAllRead: () => void;
  onLoadMore: () => void;
}

// 下拉菜单内容:
// - 标题: "通知中心" + "全部已读"按钮
// - 列表: 热点标题 + 匹配关键词 + 来源 + 时间
// - 空状态: "暂无新通知"
// - 底部: "查看更多" 或 "设置预警关键词"链接
```

### 2. AlertSettings (预警设置页)
```typescript
// 位置: /settings/alerts (新增标签页)
// 图标: Bell (lucide-react)

interface AlertSettingsProps {
  keywords: AlertKeyword[];
  onAddKeyword: (keyword: string, category?: string) => void;
  onRemoveKeyword: (id: string) => void;
  onToggleKeyword: (id: string, active: boolean) => void;
  suggestedKeywords: string[];  // AI推荐
}

// 页面结构:
// - 标题: "热点预警设置"
// - 说明: "设置关注的关键词，当热点匹配时我们会通知您"
// - AI推荐区: "根据您的文章，推荐关注以下关键词" + 可点击添加
// - 关键词输入: 输入框 + 分类选择 + 添加按钮
// - 关键词列表: 关键词 | 分类 | 开关 | 删除按钮
// - 空状态: "还没有设置关键词，添加一个开始接收预警"
```

### 3. Dashboard (数据看板)
```typescript
// 位置: /dashboard (新增页面)
// 路由: 在导航栏添加 "数据看板" 入口

interface DashboardProps {
  tier: 'free' | 'pro' | 'ultra';
  stats: UserStats;
}

// Free 用户:
// ┌─────────────────────────────────────┐
// │  总创作数    累计字数    本月生成   配额使用  │
// │   128      45,230      12/30     12/30   │
// └─────────────────────────────────────┘

// Pro 用户 (+图表):
// ┌─────────────────────────────────────┐
// │ [评分趋势图]        [平台分布饼图]   │
// │ 近30天评分变化       各平台文章占比  │
// └─────────────────────────────────────┘

// Ultra 用户 (+高级统计):
// ┌─────────────────────────────────────┐
// │ [热点匹配数] [关键词命中率] [模型使用分布] │
// │    45          68%          柱状图   │
// └─────────────────────────────────────┘
```

---

## 后台任务

### 1. alert_worker.py (定时任务)
```python
# 执行频率: 每30分钟
# 使用 ARQ 定时任务

async def scan_hotspots_and_alert(ctx):
    """
    1. 获取所有启用的关键词 (按用户分组)
    2. 获取各平台热点数据 (缓存或实时)
    3. 对每个关键词，匹配热点标题
       - 使用简单的字符串包含匹配 (case-insensitive)
       - 或使用简单的分词匹配
    4. 创建 AlertRecord
    5. 更新 UserStats.hotspot_matches
    """

    # 伪代码:
    keywords = await get_active_keywords_grouped_by_user()
    hotspots = await get_all_hotspots_from_cache()

    for user_id, user_keywords in keywords.items():
        for keyword in user_keywords:
            matched = [h for h in hotspots if keyword.keyword.lower() in h.title.lower()]
            for hotspot in matched:
                # 检查是否已存在该匹配记录 (去重)
                if not await alert_exists(user_id, keyword.id, hotspot.id):
                    await create_alert_record(user_id, keyword.id, hotspot)
                    await increment_hotspot_match_count(user_id)
```

### 2. stats_refresh_worker.py (统计刷新)
```python
# 执行频率: 每小时

async def refresh_all_user_stats(ctx):
    """每小时刷新所有用户统计数据"""
    users = await get_all_active_users()
    for user in users:
        await analytics_service.refresh_user_stats(user.id)
```

---

## 数据流

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  热点数据源   │────▶│ alert_worker │────▶│ AlertRecord  │
│ (baidu/weibo)│     │ (每30分钟)   │     │ (存储匹配)   │
└──────────────┘     └──────────────┘     └──────┬───────┘
                                                  │
                                                  ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  用户界面    │◀────│  通知API     │◀────│  查询通知    │
│ (铃铛/列表)  │     │              │     │              │
└──────────────┘     └──────────────┘     └──────────────┘

┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ 文章生成完成  │────▶│ analytics_   │────▶│  UserStats   │
│ 文章评分完成  │     │  service     │     │  (增量更新)  │
└──────────────┘     └──────────────┘     └──────────────┘

┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ stats_refresh│────▶│ 定时刷新所有 │────▶│  UserStats   │
│ _worker      │     │ 用户统计     │     │  (全量更新)  │
│ (每小时)     │     │              │     │              │
└──────────────┘     └──────────────┘     └──────────────┘
```

---

## 统计刷新触发点

| 触发时机 | 更新内容 | 更新方式 |
|---------|---------|---------|
| 文章生成完成 | total_articles, monthly_articles, total_words | 增量更新 |
| 文章评分完成 | avg_score, score_history | 增量更新 |
| 平台转换 | platform_stats | 增量更新 |
| 热点匹配 | hotspot_matches | 增量更新 |
| 每小时 | 所有统计数据 | 全量刷新 (定时任务) |

---

## 权限控制

| 功能 | Free | Pro | Ultra |
|-----|------|-----|-------|
| 设置关键词 | 1个 | 5个 | 无限制 |
| 接收预警通知 | ✅ | ✅ | ✅ |
| 基础数据看板 | ✅ | ✅ | ✅ |
| 趋势图/平台分布 | ❌ | ✅ | ✅ |
| 热点匹配统计 | ❌ | ❌ | ✅ |
| 关键词命中率 | ❌ | ❌ | ✅ |
| 模型使用分布 | ❌ | ❌ | ✅ |

---

## 开发顺序

### Phase 1: 后端基础 (Day 1-2)
1. 创建数据模型 (AlertKeyword, AlertRecord, UserStats)
2. 创建数据库迁移
3. 实现 alert_service.py
4. 实现 notification_service.py

### Phase 2: API 接口 (Day 2-3)
1. 实现 /alerts/* API
2. 实现 /notifications/* API
3. 实现 /dashboard API
4. 添加权限控制

### Phase 3: 后台任务 (Day 3-4)
1. 实现 alert_worker.py (定时扫描)
2. 实现 stats_refresh_worker.py (统计刷新)
3. 配置 ARQ 定时任务

### Phase 4: 前端组件 (Day 4-5)
1. NotificationCenter 组件
2. AlertSettings 页面
3. Dashboard 页面
4. 集成到 MainLayout

### Phase 5: 测试 (Day 5-6)
1. API 测试
2. 前端测试
3. 集成测试
4. 更新进度文档

---

*本文档完成于 2026-02-19*
