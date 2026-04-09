# SupaWriter Full-Site Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 基于全站巡检清单，先完成 P0 阻断问题修复，再统一鉴权、能力可用性、页面跳转与页面去留逻辑，恢复站点为一套可预测、可回归、可继续演进的产品结构。

**Architecture:** 先修“跨页面真相源”问题，而不是继续零散修 bug。第一阶段统一前端鉴权真相、修正关键后端接口空态/配置态、为 AI 能力建立前置 readiness gate；第二阶段统一页面跳转与权限加载时机；第三阶段再处理信息架构与占位/测试页下线。所有任务按小步提交、测试先行、单批可回归执行。

**Tech Stack:** Next.js App Router, React, TypeScript, FastAPI, Playwright, Pytest.

---

## Spec / Source of Truth

- 主巡检清单：`/Users/wxk/Desktop/workspace/supawriter/docs/full-site-test-checklist-2026-03-28.md`
- 本计划：`/Users/wxk/Desktop/workspace/supawriter/docs/superpowers/plans/2026-03-28-full-site-remediation.md`

## Execution Rules

- 每次只做一个任务，不跨 P0/P1/P2 混改。
- 每个任务都先补最小失败测试，再改实现，再跑聚焦回归。
- 前端跳转统一到 `/auth/signin`，不要继续新增 `/api/auth/signin` 或页面内各自拼 callback 逻辑。
- “能不能进入页面”和“页面内部怎么显示/拉数据”必须使用同一套鉴权真相。
- AI 能力页一律先判断“是否可用”，不能让用户点完按钮后才收到配置缺失错误。
- 暂无业务价值的页面优先隐藏/下线，不做装饰性完善。

## File Map

### Auth truth / shell
- Modify: `/Users/wxk/Desktop/workspace/supawriter/frontend/src/components/layout/Navigation.tsx`
- Modify: `/Users/wxk/Desktop/workspace/supawriter/frontend/src/hooks/useAuth.ts`
- Modify: `/Users/wxk/Desktop/workspace/supawriter/frontend/src/lib/backend-auth-storage.ts`
- Create: `/Users/wxk/Desktop/workspace/supawriter/frontend/src/lib/auth-state.ts`

### Auth routing / callback consistency
- Modify: `/Users/wxk/Desktop/workspace/supawriter/frontend/src/app/login/page.tsx`
- Modify: `/Users/wxk/Desktop/workspace/supawriter/frontend/src/app/pricing/page.tsx`
- Modify: `/Users/wxk/Desktop/workspace/supawriter/frontend/src/app/account/page.tsx`
- Modify: `/Users/wxk/Desktop/workspace/supawriter/frontend/src/app/settings/page.tsx`
- Modify: `/Users/wxk/Desktop/workspace/supawriter/frontend/src/app/settings/alerts/page.tsx`
- Modify: `/Users/wxk/Desktop/workspace/supawriter/frontend/src/app/dashboard/page.tsx`
- Modify: `/Users/wxk/Desktop/workspace/supawriter/frontend/src/app/agent/page.tsx`
- Modify: `/Users/wxk/Desktop/workspace/supawriter/frontend/src/app/batch/page.tsx`

### Capability readiness / AI degraded UX
- Create: `/Users/wxk/Desktop/workspace/supawriter/frontend/src/lib/capability-readiness.ts`
- Create: `/Users/wxk/Desktop/workspace/supawriter/frontend/src/components/system/CapabilityGate.tsx`
- Modify: `/Users/wxk/Desktop/workspace/supawriter/frontend/src/app/ai-assistant/page.tsx`
- Modify: `/Users/wxk/Desktop/workspace/supawriter/frontend/src/app/tweet-topics/components/IntelligentMode.tsx`
- Modify: `/Users/wxk/Desktop/workspace/supawriter/frontend/src/app/tweet-topics/components/ManualMode.tsx`
- Modify: `/Users/wxk/Desktop/workspace/supawriter/frontend/src/components/writer/WriterForm.tsx`

### Backend API contracts / permissions
- Modify: `/Users/wxk/Desktop/workspace/supawriter/backend/api/routes/chat.py`
- Modify: `/Users/wxk/Desktop/workspace/supawriter/backend/api/routes/tweet_topics.py`
- Modify: `/Users/wxk/Desktop/workspace/supawriter/backend/api/routes/hotspots_v2.py`

### Premium/request timing / UX consistency
- Modify: `/Users/wxk/Desktop/workspace/supawriter/frontend/src/app/hotspots/page.tsx`
- Modify: `/Users/wxk/Desktop/workspace/supawriter/frontend/src/app/dashboard/page.tsx`
- Modify: `/Users/wxk/Desktop/workspace/supawriter/frontend/src/app/agent/page.tsx`
- Modify: `/Users/wxk/Desktop/workspace/supawriter/frontend/src/app/batch/page.tsx`
- Modify: `/Users/wxk/Desktop/workspace/supawriter/frontend/src/app/history/page.tsx`
- Modify: `/Users/wxk/Desktop/workspace/supawriter/frontend/src/app/tweet-topics/components/HistoryView.tsx`
- Modify: `/Users/wxk/Desktop/workspace/supawriter/frontend/src/app/tweet-topics/components/TopicCard.tsx`
- Modify: `/Users/wxk/Desktop/workspace/supawriter/frontend/src/components/writer/SEOPanel.tsx`
- Modify: `/Users/wxk/Desktop/workspace/supawriter/frontend/src/components/writer/ScoreCard.tsx`

### Product structure / page rationalization
- Modify: `/Users/wxk/Desktop/workspace/supawriter/frontend/src/app/workspace/page.tsx`
- Modify: `/Users/wxk/Desktop/workspace/supawriter/frontend/src/app/news/page.tsx`
- Modify: `/Users/wxk/Desktop/workspace/supawriter/frontend/src/app/ai-navigator/page.tsx`
- Modify: `/Users/wxk/Desktop/workspace/supawriter/frontend/src/app/community/page.tsx`
- Modify: `/Users/wxk/Desktop/workspace/supawriter/frontend/src/app/rewrite/page.tsx`
- Modify: `/Users/wxk/Desktop/workspace/supawriter/frontend/src/app/animations-test/page.tsx`

### Tests
- Modify: `/Users/wxk/Desktop/workspace/supawriter/tests/frontend-navigation-remediation.spec.ts`
- Create: `/Users/wxk/Desktop/workspace/supawriter/tests/frontend-auth-routing-consistency.spec.ts`
- Create: `/Users/wxk/Desktop/workspace/supawriter/tests/frontend-capability-readiness.spec.ts`
- Create: `/Users/wxk/Desktop/workspace/supawriter/tests/test_chat_sessions_empty_state.py`
- Create: `/Users/wxk/Desktop/workspace/supawriter/tests/test_tweet_topics_provider_validation.py`
- Create: `/Users/wxk/Desktop/workspace/supawriter/tests/test_hotspots_permissions.py`

---

## Phase 1: P0 Blocking Fixes

### Task 1: 统一前端鉴权真相源

**Files:**
- Create: `/Users/wxk/Desktop/workspace/supawriter/frontend/src/lib/auth-state.ts`
- Modify: `/Users/wxk/Desktop/workspace/supawriter/frontend/src/hooks/useAuth.ts`
- Modify: `/Users/wxk/Desktop/workspace/supawriter/frontend/src/components/layout/Navigation.tsx`
- Modify: `/Users/wxk/Desktop/workspace/supawriter/tests/frontend-navigation-remediation.spec.ts`
- Test: `/Users/wxk/Desktop/workspace/supawriter/tests/frontend-auth-routing-consistency.spec.ts`

- [ ] **Step 1: 写失败的导航态集成测试**

```ts
import { test, expect } from '@playwright/test'

test('email password login renders authenticated navigation shell', async ({ page }) => {
  await page.goto('/auth/signin')
  await page.getByLabel('邮箱地址').fill(process.env.E2E_EMAIL!)
  await page.getByLabel('密码').fill(process.env.E2E_PASSWORD!)
  await page.getByRole('button', { name: '登录', exact: true }).click()
  await expect(page).toHaveURL(/\/writer/)
  await expect(page.getByText('登录')).toHaveCount(0)
  await expect(page.getByText('注册')).toHaveCount(0)
})
```

- [ ] **Step 2: 运行测试确认失败**

Run: `npx playwright test /Users/wxk/Desktop/workspace/supawriter/tests/frontend-navigation-remediation.spec.ts -g "authenticated navigation shell"`
Expected: FAIL，登录后页面已进入，但导航仍按游客态渲染。

- [ ] **Step 3: 写最小 auth state helper**

```ts
export function hasBackendAuthToken(): boolean {
  if (typeof window === 'undefined') return false
  return Boolean(localStorage.getItem('token'))
}

export function isClientAuthenticated(sessionStatus?: string): boolean {
  return sessionStatus === 'authenticated' || hasBackendAuthToken()
}
```

- [ ] **Step 4: 让 `useAuth` 与 `Navigation` 共用该真相源**

```ts
const isAuthenticated = isClientAuthenticated(sessionStatus)
const navItems = isAuthenticated ? memberNavItems : guestNavItems
```

- [ ] **Step 5: 回归导航与登录后显示**

Run: `npx playwright test /Users/wxk/Desktop/workspace/supawriter/tests/frontend-navigation-remediation.spec.ts /Users/wxk/Desktop/workspace/supawriter/tests/frontend-auth-routing-consistency.spec.ts`
Expected: PASS。

- [ ] **Step 6: 提交**

```bash
git add frontend/src/lib/auth-state.ts frontend/src/hooks/useAuth.ts frontend/src/components/layout/Navigation.tsx tests/frontend-navigation-remediation.spec.ts tests/frontend-auth-routing-consistency.spec.ts
git commit -m "fix: unify frontend auth truth source"
```

### Task 2: 修复聊天会话空态 500

**Files:**
- Modify: `/Users/wxk/Desktop/workspace/supawriter/backend/api/routes/chat.py`
- Create: `/Users/wxk/Desktop/workspace/supawriter/tests/test_chat_sessions_empty_state.py`

- [ ] **Step 1: 写失败的后端测试**

```python
def test_chat_sessions_returns_empty_payload_for_new_user(client, auth_headers_for_new_user):
    response = client.get('/api/v1/chat/sessions', headers=auth_headers_for_new_user)
    assert response.status_code == 200
    assert response.json()['items'] == []
    assert response.json()['total'] == 0
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest /Users/wxk/Desktop/workspace/supawriter/tests/test_chat_sessions_empty_state.py -v`
Expected: FAIL，当前返回 500。

- [ ] **Step 3: 在 `list_sessions` 中处理空结果与序列化边界**

```python
rows = cursor.fetchall() or []
if total == 0:
    return ChatSessionResponse(items=[], total=0, page=page, page_size=page_size, total_pages=0)
```

- [ ] **Step 4: 补一条聚焦日志**

```python
logger.info('chat sessions listed', extra={'user_id': current_user_id, 'total': total})
```

- [ ] **Step 5: 重新运行测试**

Run: `pytest /Users/wxk/Desktop/workspace/supawriter/tests/test_chat_sessions_empty_state.py -v`
Expected: PASS。

- [ ] **Step 6: 提交**

```bash
git add backend/api/routes/chat.py tests/test_chat_sessions_empty_state.py
git commit -m "fix: return empty chat session state for new users"
```

### Task 3: 为核心 AI 流程增加 readiness gate

**Files:**
- Create: `/Users/wxk/Desktop/workspace/supawriter/frontend/src/lib/capability-readiness.ts`
- Create: `/Users/wxk/Desktop/workspace/supawriter/frontend/src/components/system/CapabilityGate.tsx`
- Modify: `/Users/wxk/Desktop/workspace/supawriter/frontend/src/app/ai-assistant/page.tsx`
- Modify: `/Users/wxk/Desktop/workspace/supawriter/frontend/src/app/tweet-topics/components/IntelligentMode.tsx`
- Modify: `/Users/wxk/Desktop/workspace/supawriter/frontend/src/app/tweet-topics/components/ManualMode.tsx`
- Modify: `/Users/wxk/Desktop/workspace/supawriter/frontend/src/components/writer/WriterForm.tsx`
- Test: `/Users/wxk/Desktop/workspace/supawriter/tests/frontend-capability-readiness.spec.ts`

- [ ] **Step 1: 写失败的前端测试**

```ts
test('ai assistant blocks send when provider config is missing', async ({ page }) => {
  await page.goto('/ai-assistant')
  await expect(page.getByText(/请先配置|API Key|模型配置/)).toBeVisible()
  await expect(page.getByRole('button', { name: '发送' })).toBeDisabled()
})
```

- [ ] **Step 2: 运行测试确认失败**

Run: `npx playwright test /Users/wxk/Desktop/workspace/supawriter/tests/frontend-capability-readiness.spec.ts -g "blocks send"`
Expected: FAIL，当前只有请求后才报错。

- [ ] **Step 3: 定义统一 readiness 数据结构**

```ts
export interface CapabilityReadiness {
  ready: boolean
  reason?: 'missing_provider' | 'missing_model' | 'tier_blocked'
  ctaHref?: '/settings' | '/pricing'
}
```

- [ ] **Step 4: 在页面动作前渲染 gate**

```tsx
if (!readiness.ready) {
  return <CapabilityGate title="请先完成能力配置" ctaHref={readiness.ctaHref ?? '/settings'} />
}
```

- [ ] **Step 5: 回归 AI 助手 / 推文选题 / WriterForm**

Run: `npx playwright test /Users/wxk/Desktop/workspace/supawriter/tests/frontend-capability-readiness.spec.ts`
Expected: PASS。

- [ ] **Step 6: 提交**

```bash
git add frontend/src/lib/capability-readiness.ts frontend/src/components/system/CapabilityGate.tsx frontend/src/app/ai-assistant/page.tsx frontend/src/app/tweet-topics/components/IntelligentMode.tsx frontend/src/app/tweet-topics/components/ManualMode.tsx frontend/src/components/writer/WriterForm.tsx tests/frontend-capability-readiness.spec.ts
git commit -m "feat: gate unavailable AI capabilities before action"
```

### Task 4: 统一推文选题接口契约与配置错误表达

**Files:**
- Modify: `/Users/wxk/Desktop/workspace/supawriter/backend/api/routes/tweet_topics.py`
- Modify: `/Users/wxk/Desktop/workspace/supawriter/frontend/src/app/tweet-topics/components/HistoryView.tsx`
- Modify: `/Users/wxk/Desktop/workspace/supawriter/frontend/src/app/tweet-topics/components/IntelligentMode.tsx`
- Modify: `/Users/wxk/Desktop/workspace/supawriter/frontend/src/app/tweet-topics/components/ManualMode.tsx`
- Create: `/Users/wxk/Desktop/workspace/supawriter/tests/test_tweet_topics_provider_validation.py`

- [ ] **Step 1: 写失败的 provider 校验测试**

```python
def test_generate_intelligent_returns_503_when_provider_missing(client, auth_headers_for_new_user):
    response = client.post(
        '/api/v1/tweet-topics/generate-intelligent',
        json={'custom_topic': '人工智能', 'topic_count': 3},
        headers=auth_headers_for_new_user,
    )
    assert response.status_code == 503
    assert '配置' in response.json()['detail']
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest /Users/wxk/Desktop/workspace/supawriter/tests/test_tweet_topics_provider_validation.py -v`
Expected: FAIL，当前部分分支返回泛化错误。

- [ ] **Step 3: 为生成接口增加统一 preflight**

```python
providers = _get_db_llm_providers()
if not providers:
    raise HTTPException(status_code=503, detail='没有可用的 LLM 提供商配置，请先在系统设置中配置')
```

- [ ] **Step 4: 前端统一按真实返回结构读 history / error**

```ts
const message = extractApiError(error) ?? '生成失败，请稍后重试'
```

- [ ] **Step 5: 回归接口与前端主要标签页**

Run: `pytest /Users/wxk/Desktop/workspace/supawriter/tests/test_tweet_topics_provider_validation.py -v`
Run: `npx playwright test /Users/wxk/Desktop/workspace/supawriter/tests/frontend-capability-readiness.spec.ts -g "tweet topics"`
Expected: PASS。

- [ ] **Step 6: 提交**

```bash
git add backend/api/routes/tweet_topics.py frontend/src/app/tweet-topics/components/HistoryView.tsx frontend/src/app/tweet-topics/components/IntelligentMode.tsx frontend/src/app/tweet-topics/components/ManualMode.tsx tests/test_tweet_topics_provider_validation.py
git commit -m "fix: normalize tweet topics provider validation"
```

### Task 5: 将热点页运维动作收回权限范围内

**Files:**
- Modify: `/Users/wxk/Desktop/workspace/supawriter/backend/api/routes/hotspots_v2.py`
- Modify: `/Users/wxk/Desktop/workspace/supawriter/frontend/src/app/hotspots/page.tsx`
- Create: `/Users/wxk/Desktop/workspace/supawriter/tests/test_hotspots_permissions.py`

- [ ] **Step 1: 写失败的权限测试**

```python
def test_hotspots_sync_requires_authenticated_admin(client):
    response = client.post('/api/v1/hotspots/v2/sync')
    assert response.status_code in (401, 403)
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest /Users/wxk/Desktop/workspace/supawriter/tests/test_hotspots_permissions.py -v`
Expected: FAIL，当前匿名也可触发部分操作。

- [ ] **Step 3: 后端为 `sync` / `cache` 增加明确权限校验**

```python
current_user = get_current_user(...)
if not current_user.is_admin:
    raise HTTPException(status_code=403, detail='权限不足')
```

- [ ] **Step 4: 前端仅向管理员展示运维按钮，其余仅保留内容浏览**

```tsx
{isAdmin ? <AdminActions /> : null}
```

- [ ] **Step 5: 运行后端权限回归与热点页面烟测**

Run: `pytest /Users/wxk/Desktop/workspace/supawriter/tests/test_hotspots_permissions.py -v`
Expected: PASS。

- [ ] **Step 6: 提交**

```bash
git add backend/api/routes/hotspots_v2.py frontend/src/app/hotspots/page.tsx tests/test_hotspots_permissions.py
git commit -m "fix: restrict hotspots operations to authorized admins"
```

---

## Phase 2: P1 Flow Consistency and Page Logic

### Task 6: 统一认证入口与 callbackUrl 规则

**Files:**
- Modify: `/Users/wxk/Desktop/workspace/supawriter/frontend/src/app/login/page.tsx`
- Modify: `/Users/wxk/Desktop/workspace/supawriter/frontend/src/app/pricing/page.tsx`
- Modify: `/Users/wxk/Desktop/workspace/supawriter/frontend/src/app/account/page.tsx`
- Modify: `/Users/wxk/Desktop/workspace/supawriter/frontend/src/app/settings/page.tsx`
- Modify: `/Users/wxk/Desktop/workspace/supawriter/frontend/src/app/settings/alerts/page.tsx`
- Modify: `/Users/wxk/Desktop/workspace/supawriter/frontend/src/app/dashboard/page.tsx`
- Modify: `/Users/wxk/Desktop/workspace/supawriter/frontend/src/app/agent/page.tsx`
- Modify: `/Users/wxk/Desktop/workspace/supawriter/frontend/src/app/batch/page.tsx`
- Test: `/Users/wxk/Desktop/workspace/supawriter/tests/frontend-auth-routing-consistency.spec.ts`

- [ ] **Step 1: 写失败的认证入口一致性测试**

```ts
import { test, expect } from '@playwright/test'

test('protected pages redirect to auth signin with relative callback only', async ({ page }) => {
  await page.goto('/dashboard')
  await expect(page).toHaveURL(/\/auth\/signin\?callbackUrl=%2Fdashboard/)
  await expect(page.url()).not.toContain('http://')
  await expect(page.url()).not.toContain('/api/auth/signin')
})
```

- [ ] **Step 2: 运行测试确认失败**

Run: `npx playwright test /Users/wxk/Desktop/workspace/supawriter/tests/frontend-auth-routing-consistency.spec.ts -g "relative callback only"`
Expected: FAIL，当前仍残留 `/api/auth/signin` 或绝对 callback 构造。

- [ ] **Step 3: 搜索并统一替换站内登录入口与 callback helper**

```ts
export function buildSigninHref(callbackPath?: string) {
  const safeCallback = callbackPath?.startsWith('/') ? callbackPath : '/writer'
  return `/auth/signin?callbackUrl=${encodeURIComponent(safeCallback)}`
}
```

- [ ] **Step 4: 将 `/login` 改为轻量重定向语义**

```tsx
import { redirect } from 'next/navigation'

export default function LoginAliasPage() {
  redirect('/auth/signin')
}
```

- [ ] **Step 5: 运行登录跳转回归测试**

Run: `npx playwright test /Users/wxk/Desktop/workspace/supawriter/tests/frontend-auth-routing-consistency.spec.ts`
Expected: PASS。

- [ ] **Step 6: 提交**

```bash
git add frontend/src/app/login/page.tsx frontend/src/app/pricing/page.tsx frontend/src/app/account/page.tsx frontend/src/app/settings/page.tsx frontend/src/app/settings/alerts/page.tsx frontend/src/app/dashboard/page.tsx frontend/src/app/agent/page.tsx frontend/src/app/batch/page.tsx tests/frontend-auth-routing-consistency.spec.ts
git commit -m "fix: normalize auth entrypoints and callback routing"
```

Recommended commands:
- `rg -n "api/auth/signin|callbackUrl=.*http|window.location.href" /Users/wxk/Desktop/workspace/supawriter/frontend/src`
- `npx playwright test /Users/wxk/Desktop/workspace/supawriter/tests/frontend-auth-routing-consistency.spec.ts`

### Task 7: 延后高级页面的数据请求，先决出权限

**Files:**
- Modify: `/Users/wxk/Desktop/workspace/supawriter/frontend/src/app/dashboard/page.tsx`
- Modify: `/Users/wxk/Desktop/workspace/supawriter/frontend/src/app/agent/page.tsx`
- Modify: `/Users/wxk/Desktop/workspace/supawriter/frontend/src/app/batch/page.tsx`

- [ ] **Step 1: 写失败的权限时序测试**

```ts
test('premium pages do not show load failed before access decision resolves', async ({ page }) => {
  await page.goto('/dashboard')
  await expect(page.getByText(/加载失败/)).toHaveCount(0)
})
```

- [ ] **Step 2: 运行测试确认失败**

Run: `npx playwright test /Users/wxk/Desktop/workspace/supawriter/tests/frontend-auth-routing-consistency.spec.ts -g "access decision resolves"`
Expected: FAIL，当前会出现升级提示与失败提示并存。

- [ ] **Step 3: 引入 `authResolved` / `tierResolved` 前置状态**

```ts
const canLoadProtectedData = authResolved && tierResolved && hasRequiredTier
```

- [ ] **Step 4: 在权限未决或无权限时收敛渲染分支**

```tsx
if (!authResolved || !tierResolved) return <PageSkeleton />
if (!hasRequiredTier) return <UpgradePanel />
```

- [ ] **Step 5: 运行页面聚焦回归**

Run: `npx playwright test /Users/wxk/Desktop/workspace/supawriter/tests/frontend-auth-routing-consistency.spec.ts -g "premium pages"`
Expected: PASS。

- [ ] **Step 6: 提交**

```bash
git add frontend/src/app/dashboard/page.tsx frontend/src/app/agent/page.tsx frontend/src/app/batch/page.tsx tests/frontend-auth-routing-consistency.spec.ts
git commit -m "fix: defer premium page requests until auth resolves"
```

### Task 8: 修正历史页的全量搜索/筛选与交互一致性

**Files:**
- Modify: `/Users/wxk/Desktop/workspace/supawriter/frontend/src/app/history/page.tsx`
- Test: `/Users/wxk/Desktop/workspace/supawriter/tests/frontend-auth-routing-consistency.spec.ts`

- [ ] **Step 1: 写失败的历史搜索/筛选行为测试**

```ts
test('history search triggers server-side refresh instead of filtering only cached page', async ({ page }) => {
  await page.goto('/history')
  await page.getByPlaceholder(/搜索/).fill('人工智能')
  await page.getByRole('button', { name: /搜索/ }).click()
  await expect(page.getByText(/仅当前页/)).toHaveCount(0)
})
```

- [ ] **Step 2: 运行测试确认失败**

Run: `npx playwright test /Users/wxk/Desktop/workspace/supawriter/tests/frontend-auth-routing-consistency.spec.ts -g "history search"`
Expected: FAIL，当前搜索/筛选只作用于当前页缓存。

- [ ] **Step 3: 为历史页查询参数建立服务端请求路径**

```ts
const query = { page, keyword, status }
await fetchHistory(query)
```

- [ ] **Step 4: 用统一 toast 替换 `alert()`，并验证删除/下载/编辑链路**

```ts
toast.error('保存失败，请稍后重试')
```

- [ ] **Step 5: 运行历史页回归测试**

Run: `npx playwright test /Users/wxk/Desktop/workspace/supawriter/tests/frontend-auth-routing-consistency.spec.ts -g "history"`
Expected: PASS。

- [ ] **Step 6: 提交**

```bash
git add frontend/src/app/history/page.tsx tests/frontend-auth-routing-consistency.spec.ts
git commit -m "fix: make history search and filtering query-backed"
```

### Task 9: 修正升级 CTA、站内跳转与 TaskQueue 去重

**Files:**
- Modify: `/Users/wxk/Desktop/workspace/supawriter/frontend/src/components/writer/TaskQueue.tsx`
- Modify: `/Users/wxk/Desktop/workspace/supawriter/frontend/src/components/writer/SEOPanel.tsx`
- Modify: `/Users/wxk/Desktop/workspace/supawriter/frontend/src/components/writer/ScoreCard.tsx`
- Modify: `/Users/wxk/Desktop/workspace/supawriter/frontend/src/app/tweet-topics/components/TopicCard.tsx`
- Test: `/Users/wxk/Desktop/workspace/supawriter/tests/frontend-auth-routing-consistency.spec.ts`

- [ ] **Step 1: 写失败的去重与跳转测试**

```ts
test('task queue keeps repeated topic submissions as separate tasks', async ({ page }) => {
  await page.goto('/writer')
  await expect(page.getByText('同名主题')).toHaveCount(0)
})
```

- [ ] **Step 2: 运行测试确认失败**

Run: `npx playwright test /Users/wxk/Desktop/workspace/supawriter/tests/frontend-auth-routing-consistency.spec.ts -g "repeated topic submissions"`
Expected: FAIL，当前 `topic || task_id` 去重会覆盖重复主题任务。

- [ ] **Step 3: 以稳定任务主键而非主题文案去重，并统一站内跳转**

```ts
const dedupeKey = task.task_id
router.push(`/writer?topic=${encodeURIComponent(topic)}`)
```

- [ ] **Step 4: 修正升级 CTA：升级去 `/pricing`，配置去 `/settings`**

```ts
const upgradeHref = '/pricing'
const configHref = '/settings'
```

- [ ] **Step 5: 运行 TaskQueue / CTA / TopicCard 回归**

Run: `npx playwright test /Users/wxk/Desktop/workspace/supawriter/tests/frontend-auth-routing-consistency.spec.ts -g "task queue|upgrade CTA|TopicCard"`
Expected: PASS。

- [ ] **Step 6: 提交**

```bash
git add frontend/src/components/writer/TaskQueue.tsx frontend/src/components/writer/SEOPanel.tsx frontend/src/components/writer/ScoreCard.tsx frontend/src/app/tweet-topics/components/TopicCard.tsx tests/frontend-auth-routing-consistency.spec.ts
git commit -m "fix: align task queue and upgrade navigation behavior"
```

### Task 10: 收敛设置页职责边界

**Files:**
- Modify: `/Users/wxk/Desktop/workspace/supawriter/frontend/src/app/settings/page.tsx`
- Modify: `/Users/wxk/Desktop/workspace/supawriter/frontend/src/app/settings/alerts/page.tsx`

- [ ] **Step 1: 写失败的设置页职责测试**

```ts
test('settings separates personal, system, and admin sections clearly', async ({ page }) => {
  await page.goto('/settings')
  await expect(page.getByText(/个人设置/)).toBeVisible()
  await expect(page.getByText(/系统配置/)).toBeVisible()
})
```

- [ ] **Step 2: 运行测试确认失败**

Run: `npx playwright test /Users/wxk/Desktop/workspace/supawriter/tests/frontend-auth-routing-consistency.spec.ts -g "settings separates"`
Expected: FAIL，当前职责混杂且 alerts 入口重复。

- [ ] **Step 3: 将个人设置、系统配置、管理入口按分组重排**

```tsx
<SettingsSection title="个人设置" />
<SettingsSection title="系统配置" />
<SettingsSection title="管理员入口" />
```

- [ ] **Step 4: 删除旧登录兜底路径并补 alerts 空态/错误态 CTA**

```tsx
<EmptyState ctaHref="/settings" />
```

- [ ] **Step 5: 运行设置页与 alerts 回归**

Run: `npx playwright test /Users/wxk/Desktop/workspace/supawriter/tests/frontend-auth-routing-consistency.spec.ts -g "settings|alerts"`
Expected: PASS。

- [ ] **Step 6: 提交**

```bash
git add frontend/src/app/settings/page.tsx frontend/src/app/settings/alerts/page.tsx tests/frontend-auth-routing-consistency.spec.ts
git commit -m "refactor: simplify settings and alerts responsibilities"
```

---

## Phase 3: P2 IA Cleanup and De-scope

### Task 11: 明确产品主入口，只保留一个创作中心

**Files:**
- Modify: `/Users/wxk/Desktop/workspace/supawriter/frontend/src/app/workspace/page.tsx`
- Modify: `/Users/wxk/Desktop/workspace/supawriter/frontend/src/components/layout/Navigation.tsx`

- [ ] **Step 1: 写失败的主入口测试**

```ts
test('workspace no longer competes with writer as primary entry', async ({ page }) => {
  await page.goto('/workspace')
  await expect(page).toHaveURL(/\/writer|\/workspace/)
})
```

- [ ] **Step 2: 运行测试确认失败**

Run: `npx playwright test /Users/wxk/Desktop/workspace/supawriter/tests/frontend-auth-routing-consistency.spec.ts -g "primary entry"`
Expected: FAIL，当前 `/workspace` 与 `/writer` 同时承担入口语义。

- [ ] **Step 3: 将 `/workspace` 改成纯导流或轻量壳页**

```tsx
redirect('/writer')
```

- [ ] **Step 4: 去掉导航与首页中的双入口表达并回归主链路**

Run: `npx playwright test /Users/wxk/Desktop/workspace/supawriter/tests/frontend-auth-routing-consistency.spec.ts -g "writer"`
Expected: PASS。

- [ ] **Step 5: 提交**

```bash
git add frontend/src/app/workspace/page.tsx frontend/src/components/layout/Navigation.tsx tests/frontend-auth-routing-consistency.spec.ts
git commit -m "refactor: consolidate writer entrypoints"
```

### Task 12: 下线占位页和测试页

**Files:**
- Modify: `/Users/wxk/Desktop/workspace/supawriter/frontend/src/app/community/page.tsx`
- Modify: `/Users/wxk/Desktop/workspace/supawriter/frontend/src/app/rewrite/page.tsx`
- Modify: `/Users/wxk/Desktop/workspace/supawriter/frontend/src/app/animations-test/page.tsx`
- Modify: `/Users/wxk/Desktop/workspace/supawriter/frontend/src/components/layout/Navigation.tsx`

- [ ] **Step 1: 写失败的占位页/测试页暴露测试**

```ts
test('placeholder and internal test pages are not exposed in production navigation', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByText(/社区管理|文章再创作|animations-test/i)).toHaveCount(0)
})
```

- [ ] **Step 2: 运行测试确认失败**

Run: `npx playwright test /Users/wxk/Desktop/workspace/supawriter/tests/frontend-auth-routing-consistency.spec.ts -g "not exposed"`
Expected: FAIL，当前仍可访问或在导航中残留。

- [ ] **Step 3: 对 `community` / `rewrite` 执行同一去留策略**

```tsx
notFound()
```

- [ ] **Step 4: 为 `animations-test` 增加开发环境守卫并回归公开路由**

```tsx
if (process.env.NODE_ENV !== 'development') notFound()
```

- [ ] **Step 5: 提交**

```bash
git add frontend/src/app/community/page.tsx frontend/src/app/rewrite/page.tsx frontend/src/app/animations-test/page.tsx frontend/src/components/layout/Navigation.tsx tests/frontend-auth-routing-consistency.spec.ts
git commit -m "chore: hide placeholder and test-only pages"
```

### Task 13: 明确 `ai-navigator` 与 `news` 的产品边界

**Files:**
- Modify: `/Users/wxk/Desktop/workspace/supawriter/frontend/src/app/ai-navigator/page.tsx`
- Modify: `/Users/wxk/Desktop/workspace/supawriter/frontend/src/app/news/page.tsx`

- [ ] **Step 1: 写失败的页面定位/跳转测试**

```ts
test('ai navigator and news use unified auth gating and clear page CTAs', async ({ page }) => {
  await page.goto('/ai-navigator')
  await expect(page.url()).not.toContain('/api/auth/signin')
})
```

- [ ] **Step 2: 运行测试确认失败**

Run: `npx playwright test /Users/wxk/Desktop/workspace/supawriter/tests/frontend-auth-routing-consistency.spec.ts -g "ai navigator and news"`
Expected: FAIL，当前 `ai-navigator` 仍保留页面内独立鉴权逻辑。

- [ ] **Step 3: 移除独立鉴权分支，统一交给 middleware 与 auth helper**

```ts
const isAuthenticated = useAuth().isAuthenticated
```

- [ ] **Step 4: 调整 CTA、空态与返回路径并跑回归**

Run: `npx playwright test /Users/wxk/Desktop/workspace/supawriter/tests/frontend-auth-routing-consistency.spec.ts -g "ai navigator and news"`
Expected: PASS。

- [ ] **Step 5: 提交**

```bash
git add frontend/src/app/ai-navigator/page.tsx frontend/src/app/news/page.tsx tests/frontend-auth-routing-consistency.spec.ts
git commit -m "refactor: clarify ai navigator and news positioning"
```

---

## Verification Matrix

### Backend focused
- `pytest /Users/wxk/Desktop/workspace/supawriter/tests/test_chat_sessions_empty_state.py -v`
- `pytest /Users/wxk/Desktop/workspace/supawriter/tests/test_tweet_topics_provider_validation.py -v`
- `pytest /Users/wxk/Desktop/workspace/supawriter/tests/test_hotspots_permissions.py -v`

### Frontend focused
- `npx playwright test /Users/wxk/Desktop/workspace/supawriter/tests/frontend-navigation-remediation.spec.ts`
- `npx playwright test /Users/wxk/Desktop/workspace/supawriter/tests/frontend-auth-routing-consistency.spec.ts`
- `npx playwright test /Users/wxk/Desktop/workspace/supawriter/tests/frontend-capability-readiness.spec.ts`

### Broader regression
- `pytest /Users/wxk/Desktop/workspace/supawriter/tests -q`
- `npx playwright test`

---

## Suggested Commit Order

1. `fix: unify frontend auth truth source`
2. `fix: return empty chat session state for new users`
3. `feat: gate unavailable AI capabilities before action`
4. `fix: normalize tweet topics provider validation`
5. `fix: restrict hotspots operations to authorized admins`
6. `fix: normalize auth entrypoints and callback routing`
7. `fix: defer premium page requests until auth resolves`
8. `fix: make history search and filtering query-backed`
9. `fix: align task queue and upgrade navigation behavior`
10. `refactor: simplify settings and alerts responsibilities`
11. `refactor: consolidate writer entrypoints`
12. `chore: hide placeholder and test-only pages`
13. `refactor: clarify ai navigator and news positioning`

---

## Recommended Execution Order

- 先执行 Task 1 → 5，完成全部 P0。
- P0 全部通过后，再执行 Task 6 → 10。
- 最后做 Task 11 → 13 的页面去留与信息架构清理。
- 每完成一个任务，都回写 `/Users/wxk/Desktop/workspace/supawriter/docs/full-site-test-checklist-2026-03-28.md` 对应状态。

## Handoff

Plan complete and saved to `/Users/wxk/Desktop/workspace/supawriter/docs/superpowers/plans/2026-03-28-full-site-remediation.md`.

Two execution options:

1. **Subagent-Driven (recommended)** — 按任务派发子代理逐个实施、逐个复核。
2. **Inline Execution** — 在当前会话按任务顺序直接开始修复。

If execution starts now, begin with **Task 1: 统一前端鉴权真相源**.
