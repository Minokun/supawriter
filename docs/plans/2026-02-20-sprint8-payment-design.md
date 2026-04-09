# Sprint 8 设计文档：付费体系

> 创建日期: 2026-02-20
> 目标: 实现订阅管理、定价页面、配额控制

---

## 1. 功能概述

### 1.1 核心功能
- 定价页面：三列对比卡片，周期切换
- 订阅管理：当前方案、升级/降级、取消
- 配额控制：使用量追踪、额度提醒
- 额度包：独立购买的额外额度

### 1.2 暂缓功能
- 真实支付对接（微信/支付宝）
- 支付回调处理
- 自动续费

---

## 2. 定价方案

### 2.1 订阅定价

| 等级 | 月付 | 季付 | 年付 | 配额 |
|------|------|------|------|------|
| **Free** | 免费 | 免费 | 免费 | 5次/月 |
| **Pro** | ¥49/月 | ¥125/季 | ¥399/年 | 30次/月 |
| **Ultra** | ¥99/月 | ¥249/季 | ¥799/年 | 100次/月 |

**权益对比**:

| 权益 | Free | Pro | Ultra |
|------|------|-----|-------|
| 基础模型 | ✅ | ✅ | ✅ |
| 中级模型 | ❌ | ✅ | ✅ |
| 顶级模型 | ❌ | ❌ | ✅ |
| SEO优化 | ❌ | ✅ | ✅ |
| 多平台转换 | ❌ | ✅ | ✅ |
| 热点预警 | ❌ | ✅ | ✅ |
| 去水印 | ❌ | ✅ | ✅ |
| 数据看板 | 基础 | +图表 | 完整 |
| 批量生成 | ❌ | ❌ | ✅ |
| 写作Agent | ❌ | ❌ | ✅ |

### 2.2 额度包

| 额度包 | 价格 | 有效期 |
|--------|------|--------|
| 10次 | ¥19.9 | 1年 |
| 50次 | ¥79.9 | 1年 |

---

## 3. 数据模型

### 3.1 Subscription 订阅

```python
# backend/api/db/models/subscription.py

class Subscription(Base):
    """用户订阅"""
    __tablename__ = 'subscriptions'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), unique=True)

    # 订阅信息
    plan: Mapped[str] = mapped_column(String(20))  # 'pro', 'ultra'
    period: Mapped[str] = mapped_column(String(20))  # 'monthly', 'quarterly', 'yearly'
    status: Mapped[str] = mapped_column(String(20))  # 'active', 'cancelled', 'expired'

    # 周期时间
    current_period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    current_period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    # 续费设置
    auto_renew: Mapped[bool] = mapped_column(Boolean, default=False)
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="subscription")
```

### 3.2 Order 订单

```python
# backend/api/db/models/order.py

class Order(Base):
    """订单"""
    __tablename__ = 'orders'

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'))

    # 订单类型
    order_type: Mapped[str] = mapped_column(String(20))  # 'subscription', 'quota_pack'

    # 订阅相关
    plan: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # 'pro', 'ultra'
    period: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # 'monthly', 'quarterly', 'yearly'

    # 额度包相关
    pack_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # 'pack_10', 'pack_50'
    quota_amount: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # 金额
    amount_cents: Mapped[int] = mapped_column(Integer)  # 金额（分）

    # 状态
    status: Mapped[str] = mapped_column(String(20))  # 'pending', 'paid', 'cancelled'

    # 支付信息（暂缓）
    payment_method: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    payment_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
```

### 3.3 QuotaPack 额度包

```python
# backend/api/db/models/quota_pack.py

class QuotaPack(Base):
    """额度包"""
    __tablename__ = 'quota_packs'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'))

    # 额度包信息
    pack_type: Mapped[str] = mapped_column(String(20))  # 'pack_10', 'pack_50'
    total_quota: Mapped[int] = mapped_column(Integer)
    used_quota: Mapped[int] = mapped_column(Integer, default=0)
    remaining_quota: Mapped[int] = mapped_column(Integer)  # 冗余字段，方便查询

    # 关联订单
    order_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey('orders.id'), nullable=True)

    # 有效期
    purchased_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
```

---

## 4. API 设计

### 4.1 定价 API

```python
# GET /api/v1/pricing/plans
# 获取定价方案

Response:
{
    "plans": [
        {
            "id": "free",
            "name": "Free",
            "prices": {
                "monthly": 0,
                "quarterly": 0,
                "yearly": 0
            },
            "features": [...],
            "quota": 5
        },
        {
            "id": "pro",
            "name": "Pro",
            "prices": {
                "monthly": 4900,
                "quarterly": 12500,
                "yearly": 39900
            },
            "features": [...],
            "quota": 30,
            "popular": true
        },
        {
            "id": "ultra",
            "name": "Ultra",
            "prices": {
                "monthly": 9900,
                "quarterly": 24900,
                "yearly": 79900
            },
            "features": [...],
            "quota": 100
        }
    ],
    "quota_packs": [
        {"id": "pack_10", "quota": 10, "price": 1990},
        {"id": "pack_50", "quota": 50, "price": 7990}
    ]
}
```

### 4.2 订阅 API

```python
# GET /api/v1/subscription
# 获取当前用户订阅信息

Response:
{
    "current_plan": "pro",
    "current_period": "monthly",
    "status": "active",
    "current_period_end": "2026-03-20T00:00:00Z",
    "auto_renew": false,
    "quota": {
        "monthly_limit": 30,
        "monthly_used": 12,
        "pack_remaining": 10
    }
}

# POST /api/v1/subscription/upgrade
# 升级/降级订阅（模拟）

Request:
{
    "plan": "ultra",
    "period": "yearly"
}

Response:
{
    "order_id": "uuid",
    "status": "pending",
    "amount": 79900,
    "message": "订单已创建，请完成支付"
}

# POST /api/v1/subscription/cancel
# 取消订阅

Response:
{
    "message": "订阅已取消，当前周期内权益保留",
    "current_period_end": "2026-03-20T00:00:00Z"
}
```

### 4.3 配额 API

```python
# GET /api/v1/quota
# 获取配额详情

Response:
{
    "plan_quota": 30,
    "plan_used": 12,
    "plan_remaining": 18,
    "pack_quota": 10,
    "pack_used": 3,
    "pack_remaining": 7,
    "total_remaining": 25
}

# POST /api/v1/quota-packs/purchase
# 购买额度包（模拟）

Request:
{
    "pack_type": "pack_10"
}

Response:
{
    "order_id": "uuid",
    "status": "pending",
    "amount": 1990
}
```

---

## 5. 前端设计

### 5.1 定价页面 `/pricing`

```
布局:
┌─────────────────────────────────────────────────────┐
│                    定价方案                          │
│         ┌─────────┬─────────┬─────────┐             │
│         │  Free   │   Pro   │  Ultra  │             │
│         │   ¥0    │   ¥49   │   ¥99   │  ← 月/季/年切换 │
│         │  基础版  │ 最受欢迎 │  专业版  │             │
│         ├─────────┼─────────┼─────────┤             │
│         │  5次/月 │ 30次/月 │100次/月 │             │
│         │  基础模型│ 中级模型 │ 顶级模型 │             │
│         │    -    │ SEO优化 │ 批量生成 │             │
│         │    -    │ 多平台  │ 写作Agent│             │
│         │    -    │ 热点预警 │   ...   │             │
│         ├─────────┼─────────┼─────────┤             │
│         │ 当前方案 │ 立即升级 │ 立即升级 │             │
│         └─────────┴─────────┴─────────┘             │
│                                                     │
│               额度包（按需购买）                      │
│         ┌──────────────┬──────────────┐             │
│         │   10次 ¥19.9  │  50次 ¥79.9  │             │
│         └──────────────┴──────────────┘             │
└─────────────────────────────────────────────────────┘
```

### 5.2 订阅管理（设置页）

```
当前方案卡片:
┌─────────────────────────────────────────────────────┐
│ 当前方案: Pro (月付)                    [管理订阅]   │
│                                                     │
│ 配额使用: 12 / 30 次                                │
│ ████████████░░░░░░░░░░░░░░░░  40%                  │
│                                                     │
│ 额度包剩余: 10 次                                    │
│                                                     │
│ 下次续费: 2026年3月20日                             │
└─────────────────────────────────────────────────────┘
```

---

## 6. 开发任务拆分

### Phase 1: 数据模型 (0.5天)
- [ ] 创建 subscription.py 模型
- [ ] 创建 order.py 模型
- [ ] 创建 quota_pack.py 模型
- [ ] 生成数据库迁移

### Phase 2: 后端服务 (1天)
- [ ] 创建 subscription_service.py
- [ ] 创建 pricing_service.py
- [ ] 实现配额检查逻辑

### Phase 3: API 接口 (0.5天)
- [ ] 创建 pricing.py 路由
- [ ] 创建 subscription.py 路由
- [ ] 注册路由到 main.py

### Phase 4: 前端组件 (1天)
- [ ] 创建 /pricing 页面
- [ ] 更新设置页添加订阅管理
- [ ] 添加导航入口

### Phase 5: 测试验证 (0.5天)
- [ ] 功能测试
- [ ] 代码审查

---

## 7. 权限控制

| 操作 | Free | Pro | Ultra | Superuser |
|------|------|-----|-------|-----------|
| 查看定价 | ✅ | ✅ | ✅ | ✅ |
| 升级到 Pro | ✅ | - | - | - |
| 升级到 Ultra | ✅ | ✅ | - | - |
| 购买额度包 | ✅ | ✅ | ✅ | - |
| 取消订阅 | - | ✅ | ✅ | - |

---

*文档版本: 1.0*
*最后更新: 2026-02-20*
