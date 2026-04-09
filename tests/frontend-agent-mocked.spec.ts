import { expect, test, type Page, type Route } from '@playwright/test'

const APP_ORIGIN = process.env.PLAYWRIGHT_BASE_URL ?? 'http://127.0.0.1:3100'

type MembershipTier = 'free' | 'pro' | 'ultra' | 'superuser'

interface MockMemberOptions {
  membershipTier?: MembershipTier
  userId?: number
  username?: string
}

function appUrl(pathname: string): string {
  return new URL(pathname, APP_ORIGIN).toString()
}

function apiPattern(pathname: string): RegExp {
  return new RegExp(`(?:/api/backend)?${pathname.replaceAll('/', '\\/')}(?:\\?.*)?$`)
}

async function fulfillJson(route: Route, body: unknown, status = 200) {
  await route.fulfill({
    status,
    contentType: 'application/json',
    body: JSON.stringify(body),
  })
}

async function mockAuthenticatedMember(page: Page, options: MockMemberOptions = {}) {
  const membershipTier = options.membershipTier ?? 'pro'
  const userId = options.userId ?? 7
  const username = options.username ?? `${membershipTier}-agent-member`
  const token = `${membershipTier}-agent-token`

  await page.context().clearCookies()
  await page.addInitScript(
    ([authToken, memberTier, id, name]) => {
      window.localStorage.setItem('token', authToken)
      window.localStorage.setItem(
        'user',
        JSON.stringify({
          id,
          username: name,
          email: `${name}@supawriter.com`,
          display_name: name,
          membership_tier: memberTier,
          is_admin: false,
        }),
      )
    },
    [token, membershipTier, userId, username],
  )

  await page.context().addCookies([
    {
      name: 'backend-token',
      value: token,
      url: APP_ORIGIN,
      httpOnly: false,
      sameSite: 'Lax',
    },
  ])

  await page.route('**/api/auth/session**', async (route) => {
    await fulfillJson(route, {})
  })

  await page.route(apiPattern('/api/v1/auth/me'), async (route) => {
    await fulfillJson(route, {
      id: userId,
      username,
      email: `${username}@supawriter.com`,
      display_name: username,
      membership_tier: membershipTier,
      is_admin: false,
    })
  })

  await page.route(apiPattern('/api/v1/alerts/notifications/unread-count'), async (route) => {
    await fulfillJson(route, { count: 0 })
  })

  await page.route(apiPattern('/api/v1/settings/models'), async (route) => {
    await fulfillJson(route, {
      chat_model: 'longcat:LongCat-Flash-Chat',
      writer_model: 'longcat:LongCat-Flash-Chat',
    })
  })
}

test('C-007: /agent accept review updates draft status and hides review actions', async ({ page }) => {
  await mockAuthenticatedMember(page, { membershipTier: 'pro', username: 'agent-accept' })

  let reviewRequests: Array<{ action: string }> = []
  let draftState: 'completed' | 'reviewed' = 'completed'

  const agent = {
    id: 'agent-1',
    name: '热点追踪 Agent',
    trigger_rules: { sources: ['weibo'], keywords: ['AI'], min_heat: 100000 },
    platform: 'wechat',
    max_daily: 5,
    today_triggered: 1,
    total_triggered: 12,
    is_active: true,
  }

  const draft = () => ({
    id: 'draft-1',
    agent_id: 'agent-1',
    agent_name: '热点追踪 Agent',
    hotspot_title: 'AI 主题热搜',
    hotspot_heat: 280000,
    status: draftState,
    created_at: '2026-03-30T09:00:00.000Z',
    article_id: draftState === 'reviewed' ? 'article-1' : null,
  })

  await page.route(apiPattern('/api/v1/agents$'), async (route) => {
    await fulfillJson(route, { agents: [agent] })
  })

  await page.route(apiPattern('/api/v1/agents/drafts'), async (route) => {
    await fulfillJson(route, {
      items: [draft()],
      total: 1,
      page: 1,
      limit: 20,
      pages: 1,
    })
  })

  await page.route(apiPattern('/api/v1/agents/drafts/draft-1/review'), async (route) => {
    const body = route.request().postDataJSON() as { action: string }
    reviewRequests.push(body)
    draftState = body.action === 'accept' ? 'reviewed' : draftState
    await fulfillJson(route, { message: 'ok' })
  })

  await page.goto(appUrl('/agent'), { waitUntil: 'domcontentloaded' })
  await page.getByRole('button', { name: '草稿箱' }).click()

  await expect(page.getByText('AI 主题热搜')).toBeVisible()
  await expect(page.getByRole('button', { name: '接受' })).toBeVisible()
  await expect(page.getByRole('button', { name: '丢弃' })).toBeVisible()

  await page.getByRole('button', { name: '接受' }).click()

  await expect.poll(() => reviewRequests.length).toBe(1)
  await expect(reviewRequests[0]).toEqual({ action: 'accept' })
  await expect(page.getByText('已接受草稿')).toBeVisible()
  await expect(page.getByText('已接受', { exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: '接受' })).toHaveCount(0)
  await expect(page.getByRole('button', { name: '丢弃' })).toHaveCount(0)
  await expect(page.getByRole('button', { name: '查看' })).toBeVisible()
})

test('C-007: /agent discard review updates draft status and removes view action', async ({ page }) => {
  await mockAuthenticatedMember(page, { membershipTier: 'pro', username: 'agent-discard' })

  let reviewRequests: Array<{ action: string }> = []
  let draftState: 'completed' | 'discarded' = 'completed'

  const agent = {
    id: 'agent-2',
    name: '话题筛选 Agent',
    trigger_rules: { sources: ['zhihu'], keywords: ['产品'], min_heat: 50000 },
    platform: 'wechat',
    max_daily: 3,
    today_triggered: 0,
    total_triggered: 8,
    is_active: true,
  }

  const draft = () => ({
    id: 'draft-2',
    agent_id: 'agent-2',
    agent_name: '话题筛选 Agent',
    hotspot_title: '产品经理讨论热榜',
    hotspot_heat: 168000,
    status: draftState,
    created_at: '2026-03-30T10:00:00.000Z',
    article_id: null,
  })

  await page.route(apiPattern('/api/v1/agents$'), async (route) => {
    await fulfillJson(route, { agents: [agent] })
  })

  await page.route(apiPattern('/api/v1/agents/drafts'), async (route) => {
    await fulfillJson(route, {
      items: [draft()],
      total: 1,
      page: 1,
      limit: 20,
      pages: 1,
    })
  })

  await page.route(apiPattern('/api/v1/agents/drafts/draft-2/review'), async (route) => {
    const body = route.request().postDataJSON() as { action: string }
    reviewRequests.push(body)
    draftState = body.action === 'discard' ? 'discarded' : draftState
    await fulfillJson(route, { message: 'ok' })
  })

  await page.goto(appUrl('/agent'), { waitUntil: 'domcontentloaded' })
  await page.getByRole('button', { name: '草稿箱' }).click()

  await expect(page.getByText('产品经理讨论热榜')).toBeVisible()
  await page.getByRole('button', { name: '丢弃' }).click()

  await expect.poll(() => reviewRequests.length).toBe(1)
  await expect(reviewRequests[0]).toEqual({ action: 'discard' })
  await expect(page.getByText('已丢弃草稿')).toBeVisible()
  await expect(page.getByText('已丢弃', { exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: '接受' })).toHaveCount(0)
  await expect(page.getByRole('button', { name: '丢弃' })).toHaveCount(0)
  await expect(page.getByRole('button', { name: '查看' })).toHaveCount(0)
})

test('C-007: /agent shows backend detail on first-load failure and recovers after retry', async ({ page }) => {
  await mockAuthenticatedMember(page, { membershipTier: 'pro', username: 'agent-load-error' })

  let shouldFailAgents = true
  let shouldFailDrafts = true

  await page.route(apiPattern('/api/v1/agents$'), async (route) => {
    if (shouldFailAgents) {
      await fulfillJson(route, { detail: 'Agent 服务暂不可用' }, 503)
      return
    }

    await fulfillJson(route, { agents: [] })
  })

  await page.route(apiPattern('/api/v1/agents/drafts'), async (route) => {
    if (shouldFailDrafts) {
      await fulfillJson(route, { detail: '草稿服务暂不可用' }, 503)
      return
    }

    await fulfillJson(route, {
      items: [],
      total: 0,
      page: 1,
      limit: 20,
      pages: 1,
    })
  })

  await page.goto(appUrl('/agent'), { waitUntil: 'domcontentloaded' })

  await expect(page.getByRole('heading', { name: '加载写作 Agent 失败' })).toBeVisible()
  await expect(page.locator('main').getByText('草稿服务暂不可用').first()).toBeVisible()

  shouldFailAgents = false
  shouldFailDrafts = false
  await page.getByRole('button', { name: '重新加载' }).click()

  await expect(page.getByRole('heading', { name: '加载写作 Agent 失败' })).toHaveCount(0)
  await expect(page.getByRole('heading', { name: '还没有写作Agent' })).toBeVisible()
})

test('C-007: /agent create failure surfaces backend detail to the user', async ({ page }) => {
  await mockAuthenticatedMember(page, { membershipTier: 'pro', username: 'agent-create-error' })

  await page.route(apiPattern('/api/v1/agents$'), async (route) => {
    if (route.request().method() === 'POST') {
      await fulfillJson(route, { detail: 'Agent 名称已存在' }, 422)
      return
    }

    await fulfillJson(route, { agents: [] })
  })

  await page.route(apiPattern('/api/v1/agents/drafts'), async (route) => {
    await fulfillJson(route, {
      items: [],
      total: 0,
      page: 1,
      limit: 20,
      pages: 1,
    })
  })

  await page.goto(appUrl('/agent'), { waitUntil: 'domcontentloaded' })

  await page.getByRole('button', { name: '新建Agent' }).first().click()
  await page.getByPlaceholder('例如：科技热点追踪').fill('测试 Agent')
  await page.getByRole('button', { name: '百度热搜' }).click()
  await page.getByRole('button', { name: '创建Agent' }).last().click()

  await expect(page.getByText('Agent 名称已存在')).toBeVisible()
})
