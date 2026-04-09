# Frontend Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the confirmed frontend routing, navigation, auth-flow, dead-link, and degraded-page issues while simplifying the product surface so the main writing workflow becomes clearer.

**Architecture:** Keep the current Next.js app structure, but reduce user-facing complexity by tightening route ownership: a clear public home, a clear authenticated writing entry, fewer “开发中” surfaces in global navigation, and predictable auth guards. Use existing App Router pages, middleware, and Playwright coverage rather than introducing new frameworks or large refactors.

**Tech Stack:** Next.js 14 App Router, React 18, TypeScript, NextAuth, Playwright, existing `tests/playwright.config.ts`

---

## Spec / Context

- Audit spec: `docs/frontend-audit-2026-03-28.md`
- Existing navigation owner: `frontend/src/components/layout/Navigation.tsx`
- Existing auth gate: `frontend/src/middleware.ts`
- Existing route shells:
  - `frontend/src/app/page.tsx`
  - `frontend/src/app/workspace/page.tsx`
  - `frontend/src/app/writer/page.tsx`
  - `frontend/src/app/auth/signin/page.tsx`
  - `frontend/src/app/auth/error/page.tsx`
  - `frontend/src/app/ai-navigator/page.tsx`
  - `frontend/src/app/community/page.tsx`
  - `frontend/src/app/rewrite/page.tsx`
  - `frontend/src/app/pricing/page.tsx`
  - `frontend/src/app/hotspots/page.tsx`
- Existing backend URL helper: `frontend/src/lib/server-backend-url.ts`
- Existing server proxy routes:
  - `frontend/src/app/api/hotspots/v2/latest/[source]/route.ts`
  - `frontend/src/app/api/hotspots/v2/sources/route.ts`

## File Structure / Ownership

### Files to Modify
- `frontend/src/app/page.tsx`
  - Replace the unconditional redirect with a true public landing page or a deterministic auth-aware entry page.
- `frontend/src/app/auth/error/page.tsx`
  - Make the recovery CTA lead somewhere useful for signed-out users.
- `frontend/src/app/auth/signin/page.tsx`
  - Remove dead links and align post-login destination with the chosen primary workflow.
- `frontend/src/components/layout/Navigation.tsx`
  - Reduce top-level navigation clutter and hide unfinished/low-value routes.
- `frontend/src/middleware.ts`
  - Make auth behavior consistent for protected routes.
- `frontend/src/app/workspace/page.tsx`
  - Reposition as secondary dashboard or simplify if `writer` becomes the primary entry.
- `frontend/src/app/ai-navigator/page.tsx`
  - Remove broken internal links and optionally demote or slim the page.
- `frontend/src/app/community/page.tsx`
  - Either hide from main nav or convert into a clearly marked placeholder not shown globally.
- `frontend/src/app/rewrite/page.tsx`
  - Either hide from main nav or add a stronger placeholder strategy.
- `frontend/src/app/pricing/page.tsx`
  - Add an inline error state and retry path when pricing APIs fail.
- `frontend/src/lib/server-backend-url.ts`
  - Default to a local-safe backend URL strategy.
- `frontend/src/app/api/hotspots/v2/latest/[source]/route.ts`
  - Keep proxy behavior stable after backend URL helper changes.
- `frontend/src/app/api/hotspots/v2/sources/route.ts`
  - Keep proxy behavior stable after backend URL helper changes.

### Files to Create
- `tests/frontend-navigation-remediation.spec.ts`
  - Playwright coverage for home/auth/nav/dead-link regressions.
- `tests/frontend-backend-fallback.spec.ts`
  - Playwright/API coverage for pricing and hotspots degraded-state behavior.

### Files to Verify But Usually Not Modify
- `tests/playwright.config.ts`
- `frontend/package.json`
- `docs/frontend-audit-2026-03-28.md`

## Implementation Notes

- Prefer **removing or hiding unfinished UI** over building placeholder experiences no one should use yet.
- Prefer **one consistent auth model**:
  - public marketing/info pages are public
  - productive app pages require login
  - premium pages may render upgrade messaging only after login
- Prefer **clear primary CTA**:
  - signed out: learn product + sign in
  - signed in: go create content
- Use **minimal code** to make tests pass. No broad redesign beyond the audited scope.
- Commit after each task.

---

### Task 1: Lock Home/Auth Recovery Behavior

**Files:**
- Modify: `frontend/src/app/page.tsx`
- Modify: `frontend/src/app/auth/error/page.tsx`
- Test: `tests/frontend-navigation-remediation.spec.ts`

- [ ] **Step 1: Write the failing Playwright tests**

```ts
import { test, expect } from '@playwright/test';

test('NAV-001: signed-out home renders public entry instead of redirect loop', async ({ page }) => {
  await page.context().clearCookies();
  await page.goto('http://localhost:3000/');
  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
});

test('NAV-002: auth error recovery stays on a public route', async ({ page }) => {
  await page.goto('http://localhost:3000/auth/error?error=Default');
  await page.getByRole('link', { name: '返回首页' }).click();
  await expect(page).not.toHaveURL(/auth\/signin\?callbackUrl=/);
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `npx playwright test tests/frontend-navigation-remediation.spec.ts --config=tests/playwright.config.ts --grep "NAV-001|NAV-002"`

Expected: FAIL because `/` currently redirects into a protected flow and auth recovery is not user-friendly.

- [ ] **Step 3: Implement the minimal route fix**

```tsx
// frontend/src/app/page.tsx
export default function HomePage() {
  return <PublicLandingPage />;
}
```

```tsx
// frontend/src/app/auth/error/page.tsx
<Link href="/login">重新登录</Link>
<Link href="/">返回首页</Link>
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `npx playwright test tests/frontend-navigation-remediation.spec.ts --config=tests/playwright.config.ts --grep "NAV-001|NAV-002"`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/app/page.tsx frontend/src/app/auth/error/page.tsx tests/frontend-navigation-remediation.spec.ts
git commit -m "fix: stabilize public home and auth recovery"
```

---

### Task 2: Remove Dead Links From Sign-In Flow

**Files:**
- Modify: `frontend/src/app/auth/signin/page.tsx`
- Modify: `frontend/src/app/auth/register/page.tsx`
- Test: `tests/frontend-navigation-remediation.spec.ts`

- [ ] **Step 1: Write the failing test for dead links**

```ts
test('NAV-003: sign-in page exposes only valid local actions', async ({ page }) => {
  await page.goto('http://localhost:3000/auth/signin');
  await expect(page.getByRole('link', { name: '立即注册' })).toHaveAttribute('href', '/auth/register');
  await expect(page.getByRole('link', { name: '忘记密码？' })).not.toHaveAttribute('href', '/auth/forgot-password');
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `npx playwright test tests/frontend-navigation-remediation.spec.ts --config=tests/playwright.config.ts --grep "NAV-003"`

Expected: FAIL because the page currently links to a missing `/auth/forgot-password`.

- [ ] **Step 3: Implement the minimal link cleanup**

```tsx
// Option A: remove the link entirely until the feature exists
// Option B: replace with plain helper text
<p className="text-primary">暂不支持密码找回，请联系管理员</p>
```

```tsx
// replace placeholder legal anchors with real routes only if routes exist;
// otherwise render plain text instead of "#"
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `npx playwright test tests/frontend-navigation-remediation.spec.ts --config=tests/playwright.config.ts --grep "NAV-003"`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/app/auth/signin/page.tsx frontend/src/app/auth/register/page.tsx tests/frontend-navigation-remediation.spec.ts
git commit -m "fix: remove invalid auth page links"
```

---

### Task 3: Unify Global Navigation Around Real Product Value

**Files:**
- Modify: `frontend/src/components/layout/Navigation.tsx`
- Modify: `frontend/src/app/workspace/page.tsx`
- Modify: `frontend/src/app/ai-navigator/page.tsx`
- Modify: `frontend/src/app/community/page.tsx`
- Modify: `frontend/src/app/rewrite/page.tsx`
- Test: `tests/frontend-navigation-remediation.spec.ts`

- [ ] **Step 1: Write the failing navigation audit test**

```ts
test('NAV-004: global navigation hides unfinished or broken destinations', async ({ page }) => {
  await page.goto('http://localhost:3000/');
  await expect(page.getByText('社区管理')).toHaveCount(0);
  await expect(page.getByText('文章再创作')).toHaveCount(0);
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `npx playwright test tests/frontend-navigation-remediation.spec.ts --config=tests/playwright.config.ts --grep "NAV-004"`

Expected: FAIL because the current nav exposes unfinished routes.

- [ ] **Step 3: Implement the minimal information-architecture cleanup**

```ts
const navItems = [
  { name: 'AI助手', path: '/ai-assistant', icon: '🤖' },
  {
    name: '创作中心',
    children: [
      { name: '超能写手', path: '/writer', icon: '✍️' },
      { name: '推文选题', path: '/tweet-topics', icon: '💡' },
      { name: '历史记录', path: '/history', icon: '📚' },
    ],
  },
  { name: '热点中心', path: '/hotspots', icon: '🔥' },
  { name: '定价方案', path: '/pricing', icon: '💎' },
];
```

```tsx
// workspace becomes optional secondary dashboard, not required first stop
// ai-navigator keeps only valid links or is removed from global nav
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `npx playwright test tests/frontend-navigation-remediation.spec.ts --config=tests/playwright.config.ts --grep "NAV-004"`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/layout/Navigation.tsx frontend/src/app/workspace/page.tsx frontend/src/app/ai-navigator/page.tsx frontend/src/app/community/page.tsx frontend/src/app/rewrite/page.tsx tests/frontend-navigation-remediation.spec.ts
git commit -m "refactor: simplify global navigation"
```

---

### Task 4: Make Auth Guards Predictable

**Files:**
- Modify: `frontend/src/middleware.ts`
- Modify: `frontend/src/app/account/page.tsx`
- Modify: `frontend/src/app/agent/page.tsx`
- Modify: `frontend/src/app/dashboard/page.tsx`
- Modify: `frontend/src/app/batch/page.tsx`
- Test: `tests/frontend-navigation-remediation.spec.ts`

- [ ] **Step 1: Write the failing auth-consistency tests**

```ts
test('NAV-005: signed-out user is redirected before entering protected app pages', async ({ page }) => {
  await page.context().clearCookies();
  await page.goto('http://localhost:3000/account');
  await expect(page).toHaveURL(/auth\/signin/);
});

test('NAV-006: premium pages do not mix signed-out and upgrade states', async ({ page }) => {
  await page.context().clearCookies();
  await page.goto('http://localhost:3000/agent');
  await expect(page).toHaveURL(/auth\/signin/);
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `npx playwright test tests/frontend-navigation-remediation.spec.ts --config=tests/playwright.config.ts --reporter=list --grep "NAV-005|NAV-006"`

Expected: FAIL because several app pages currently render “请先登录” in-page instead of redirecting consistently.

- [ ] **Step 3: Implement the minimal guard alignment**

```ts
export const config = {
  matcher: [
    '/writer/:path*',
    '/ai-assistant/:path*',
    '/ai-navigator/:path*',
    '/tweet-topics/:path*',
    '/rewrite/:path*',
    '/history/:path*',
    '/news/:path*',
    '/community/:path*',
    '/settings/:path*',
    '/workspace/:path*',
    '/account/:path*',
    '/agent/:path*',
    '/dashboard/:path*',
    '/batch/:path*',
  ],
};
```

```tsx
// Keep upgrade messaging only for authenticated users who lack the right tier.
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `npx playwright test tests/frontend-navigation-remediation.spec.ts --config=tests/playwright.config.ts --reporter=list --grep "NAV-005|NAV-006"`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/middleware.ts frontend/src/app/account/page.tsx frontend/src/app/agent/page.tsx frontend/src/app/dashboard/page.tsx frontend/src/app/batch/page.tsx tests/frontend-navigation-remediation.spec.ts
git commit -m "fix: align auth gates across app routes"
```

---

### Task 5: Fix Broken Internal Routes In AI Navigator

**Files:**
- Modify: `frontend/src/app/ai-navigator/page.tsx`
- Test: `tests/frontend-navigation-remediation.spec.ts`

- [ ] **Step 1: Write the failing broken-route test**

```ts
test('NAV-009: ai navigator contains no missing internal routes', async ({ page }) => {
  await page.goto('http://localhost:3000/ai-navigator');
  const brokenLink = page.locator('a[href="/ddgs-search"]');
  await expect(brokenLink).toHaveCount(0);
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `npx playwright test tests/frontend-navigation-remediation.spec.ts --config=tests/playwright.config.ts --reporter=list --grep "NAV-009"`

Expected: FAIL because `/ddgs-search` does not exist.

- [ ] **Step 3: Implement the minimal fix**

```tsx
// Replace /ddgs-search with a valid external URL or remove the card
// Do not keep any internal href unless it resolves to an existing App Router page
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `npx playwright test tests/frontend-navigation-remediation.spec.ts --config=tests/playwright.config.ts --reporter=list --grep "NAV-009"`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/app/ai-navigator/page.tsx tests/frontend-navigation-remediation.spec.ts
git commit -m "fix: remove broken internal navigator links"
```

---

### Task 6: Make Pricing Failure States Actionable

**Files:**
- Modify: `frontend/src/app/pricing/page.tsx`
- Test: `tests/frontend-backend-fallback.spec.ts`

- [ ] **Step 1: Write the failing degraded-state test**

```ts
test('DEG-001: pricing page shows inline error state when backend is unavailable', async ({ page }) => {
  await page.goto('http://localhost:3000/pricing');
  await expect(page.getByText('加载定价信息失败')).toBeVisible();
  await expect(page.getByRole('button', { name: '重试' })).toBeVisible();
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `npx playwright test tests/frontend-backend-fallback.spec.ts --config=tests/playwright.config.ts --grep "DEG-001"`

Expected: FAIL because the page currently only emits a toast and leaves the content sparse.

- [ ] **Step 3: Implement the minimal inline error UI**

```tsx
if (errorState) {
  return (
    <MainLayout>
      <ErrorCard
        title="加载定价信息失败"
        description="请确认后端服务已启动后重试"
        onRetry={loadPricingData}
      />
    </MainLayout>
  );
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `npx playwright test tests/frontend-backend-fallback.spec.ts --config=tests/playwright.config.ts --grep "DEG-001"`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/app/pricing/page.tsx tests/frontend-backend-fallback.spec.ts
git commit -m "fix: add actionable pricing error state"
```

---

### Task 7: Make Hotspots Proxy Safe Outside Docker

**Files:**
- Modify: `frontend/src/lib/server-backend-url.ts`
- Modify: `frontend/src/app/api/hotspots/v2/latest/[source]/route.ts`
- Modify: `frontend/src/app/api/hotspots/v2/sources/route.ts`
- Test: `tests/frontend-backend-fallback.spec.ts`

- [ ] **Step 1: Write the failing route-level regression test**

```ts
test('DEG-002: hotspots proxy does not default to docker-only hostname', async ({ request }) => {
  const response = await request.get('http://localhost:3000/api/hotspots/v2/sources');
  expect(response.status()).not.toBe(500);
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `npx playwright test tests/frontend-backend-fallback.spec.ts --config=tests/playwright.config.ts --grep "DEG-002"`

Expected: FAIL or return 500 when the helper falls back to `http://backend:8000`.

- [ ] **Step 3: Implement the minimal backend URL fix**

```ts
export function getInternalApiUrl(): string {
  return (
    process.env.INTERNAL_API_URL ||
    process.env.API_PROXY_URL ||
    process.env.NEXT_PUBLIC_API_URL ||
    'http://localhost:8000'
  );
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `npx playwright test tests/frontend-backend-fallback.spec.ts --config=tests/playwright.config.ts --grep "DEG-002"`

Expected: PASS (or at minimum no Docker-hostname resolution failure)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/server-backend-url.ts frontend/src/app/api/hotspots/v2/latest/[source]/route.ts frontend/src/app/api/hotspots/v2/sources/route.ts tests/frontend-backend-fallback.spec.ts
git commit -m "fix: use local-safe backend fallback for hotspots proxy"
```

---

### Task 8: Run Full Focused Verification

**Files:**
- Verify only:
  - `frontend/src/app/page.tsx`
  - `frontend/src/app/auth/error/page.tsx`
  - `frontend/src/app/auth/signin/page.tsx`
  - `frontend/src/components/layout/Navigation.tsx`
  - `frontend/src/middleware.ts`
  - `frontend/src/app/pricing/page.tsx`
  - `frontend/src/lib/server-backend-url.ts`
  - `tests/frontend-navigation-remediation.spec.ts`
  - `tests/frontend-backend-fallback.spec.ts`

- [ ] **Step 1: Run focused Playwright coverage**

Run: `npx playwright test tests/frontend-navigation-remediation.spec.ts tests/frontend-backend-fallback.spec.ts --config=tests/playwright.config.ts`

Expected: PASS

- [ ] **Step 2: Run frontend lint**

Run: `cd frontend && npm run lint`

Expected: no new lint errors; existing warnings are acceptable only if unchanged and documented

- [ ] **Step 3: Run production build**

Run: `cd frontend && npm run build`

Expected: PASS

- [ ] **Step 4: Update audit doc status note**

```md
## Remediation Status
- [x] Home/auth flow repaired
- [x] Dead links removed
- [x] Navigation reduced
- [x] Pricing degraded state improved
- [x] Hotspots backend fallback fixed
```

- [ ] **Step 5: Commit**

```bash
git add docs/frontend-audit-2026-03-28.md
git add frontend tests
git commit -m "test: verify frontend remediation end to end"
```

---

## Out of Scope

- Rebuilding the entire design system
- Implementing full community publishing
- Implementing full rewrite workflow
- Building a full forgot-password flow
- Migrating the entire auth stack away from current cookies/session approach

## Implementation Order

1. Public home + auth recovery
2. Dead link cleanup
3. Navigation reduction
4. Auth consistency
5. Broken internal route cleanup
6. Pricing degraded state
7. Hotspots backend fallback
8. Focused verification
