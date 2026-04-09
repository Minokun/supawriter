# 我的套餐 — 定价页面重构设计

## Context

当前 `/pricing` 页面存在以下问题：
1. **命名不当**：标题是"定价方案"，应改为"我的套餐"
2. **价格 fallback 不一致**：前端 `FALLBACK_PLANS` 价格(¥19.90/¥39.90) 与后端实际价格(¥49/¥99) 差距 2.5 倍
3. **类型/API 双重定义**：`types/api.ts` 和 `lib/api/billing.ts` 各有一套类型和 API 客户端，pricing 页面用前者，SubscriptionManagement 用后者
4. **降级逻辑散布在 4+ 处**：handleUpgrade / getButtonText / getButtonVariant / button disabled 属性各自独立判断
5. **不显示订阅时间信息**：已付费用户看不到到期时间、续费状态
6. **auto_renew 永远为 False**：后端硬编码 `auto_renew=False`，但前端 UI 显示"自动续费已开启"文案

目标：重构为「套餐管理 + 升级入口」页面，已登录用户看到当前套餐详情 + 可升级方案。

## Requirements

### R1: 页面重命名
- 页面标题改为"我的套餐"
- Navigation 侧边栏文案从"定价方案"改为"我的套餐"
- 浏览器标题设置 metadata

### R2: 已登录用户 — 当前套餐信息卡片
- 顶部大卡片展示当前方案名称、计费周期、状态
- 显示到期时间（如有订阅）
- 显示配额进度条（plan_used / monthly_limit + pack_remaining）
- 显示续费状态（自动续费 / 到期后失效）
- 付费用户提供"取消订阅"按钮（取消后当前周期内权益保留）

### R3: 已登录用户 — 升级方案
- 只显示比当前等级高的方案卡片
- Free 用户看到 Pro + Ultra
- Pro 用户只看到 Ultra
- Ultra 用户不显示升级区域（已是最高级）
- 不显示降级选项

### R4: 未登录用户
- 显示完整的 3 个方案卡片 + 升级引导
- 点击升级按钮跳转登录页

### R5: 额度包
- 保留额度包购买区域

### R6: FAQ
- 保留 FAQ，更新降级相关回答

### R7: 类型/API 统一
- 删除 `types/api.ts` 中重复的 pricing/subscription/quota 类型和 API 对象（lines 1138-1276）
- pricing 页面改为从 `lib/api/billing.ts` 导入
- 统一使用 `billing.ts` 中的类型定义

### R8: 价格 fallback 修正
- `FALLBACK_PLANS` 价格与后端 `PricingService.PLANS` 对齐
- Pro: monthly=4900, quarterly=12500, yearly=39900
- Ultra: monthly=9900, quarterly=24900, yearly=79900

## Design

### 页面布局

```
┌──────────────────────────────────────┐
│  👑 我的套餐                          │
│  管理您的订阅方案与配额                │
├──────────────────────────────────────┤
│                                      │
│  ┌─── 当前套餐 ───────────────────┐  │
│  │  Pro · 月付 · 生效中           │  │
│  │  到期: 2026-05-06              │  │
│  │  ○ 续费方式: 到期后失效         │  │
│  │                                │  │
│  │  方案配额: ████████░░ 12/30   │  │
│  │  额度包剩余: 8 次              │  │
│  │                                │  │
│  │  [取消订阅]                    │  │
│  └────────────────────────────────┘  │
│                                      │
│  升级方案                            │  ← Free/Pro 才显示
│  ┌─── Ultra ─────────────────────┐  │
│  │  ¥99/月  |  ¥249/季  | ¥799/年│  │
│  │  · 顶级模型                    │  │
│  │  · 100次/月 · 批量生成 ...     │  │
│  │  [立即升级]                    │  │
│  └────────────────────────────────┘  │
│                                      │
│  额度包                              │
│  ┌─ 10次 ¥19.90 ─┐ ┌─ 50次 ¥79.90 ┐│
│  │  [购买]        │ │  [购买]       ││
│  └────────────────┘ └───────────────┘│
│                                      │
│  常见问题 ▼                          │
└──────────────────────────────────────┘
```

### 周期选择器
- 移到升级方案卡片内部（每个卡片内的 tab），不再全局切换
- 原因：当前套餐的周期是固定的，只有升级时才需要选择

### 关键组件改动

**`/pricing/page.tsx`** — 完全重写
- 移除全局周期切换器
- 添加「当前套餐」信息卡片（调用 `subscriptionApi.get()`）
- 添加条件升级卡片区域（只展示可升级方案）
- 保留额度包和 FAQ
- 所有 API 调用统一走 `billing.ts`

**`Navigation.tsx`** — 改文案
- `'定价方案'` → `'我的套餐'`

**`types/api.ts`** — 删除重复
- 删除 lines 1138-1276（重复的类型定义和 API 对象）
- 确认无其他文件从 `types/api.ts` 导入 pricing 相关内容

### 需要修改的文件

| File | Change |
|------|--------|
| `frontend/src/app/pricing/page.tsx` | 重写：新的页面布局和逻辑 |
| `frontend/src/components/layout/Navigation.tsx` | 侧边栏文案改为"我的套餐" |
| `frontend/src/types/api.ts` | 删除 lines 1138-1276 重复定义 |

### 不修改的文件

- `lib/api/billing.ts` — 已有完善的 API 客户端，无需改动
- `SubscriptionManagement.tsx` — settings 页面的订阅管理独立，本次不改
- `backend/` — 后端无需改动，已返回所有需要的数据

## Verification

1. `cd frontend && npm run build` 通过
2. Free 用户：看到当前套餐(Free) + Pro/Ultra 升级卡片
3. Pro 用户：看到当前套餐(Pro, 到期时间, 配额) + Ultra 升级卡片
4. Ultra 用户：只看到当前套餐(Ultra, 到期时间, 配额)，无升级区域
5. 未登录用户：看到 3 个方案卡片 + 登录引导
6. 无降级按钮
7. 价格与后端一致
