import { expect, test, type Page, type Route } from '@playwright/test'

const APP_ORIGIN = process.env.PLAYWRIGHT_BASE_URL ?? 'http://127.0.0.1:3100'

type MembershipTier = 'free' | 'pro' | 'ultra' | 'superuser'
type DraftStatus = 'completed' | 'reviewed' | 'discarded'

interface MockMemberOptions {
  membershipTier?: MembershipTier
  userId?: number
  username?: string
}

interface DraftRecord {
  id: string
  agent_name: string
  hotspot_title: string
  hotspot_source: string
  hotspot_heat?: number
  status: DraftStatus
  article_id?: string
  created_at: string
}

function appUrl(pathname: string): string {
  return new URL(pathname, APP_ORIGIN).toString()
}

function agentApiPattern(pathname: string): RegExp {
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
  const userId = options.userId ?? 42
  const username = options.username ?? `${membershipTier}-member`
  const token = `${membershipTier}-member-token`

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

  await page.route(agentApiPattern('/api/v1/auth/me'), async (route) => {
    await fulfillJson(route, {
      id: userId,
      username,
      email: `${username}@supawriter.com`,
      display_name: username,
      membership_tier: membershipTier,
      is_admin: false,
    })
  })

  await page.route(agentApiPattern('/api/v1/alerts/notifications/unread-count'), async (route) => {
    await fulfillJson(route, { count: 0 })
  })

  await page.route(agentApiPattern('/api/v1/settings/models'), async (route) => {
    await fulfillJson(route, {
      chat_model: 'longcat:LongCat-Flash-Chat',
      writer_model: 'longcat:LongCat-Flash-Chat',
    })
  })
}

async function mockAgentData(page: Page, initialDraftStatus: DraftStatus, finalDraftStatus: DraftStatus) {
  let currentDraftStatus = initialDraftStatus
  let reviewAction: 'accept' | 'discard' | null = null
  let reviewRequests = 0

  const draftBase: Omit<DraftRecord, 'status'> = {
    id: 'draft-review-1',
    agent_name: '热点追踪 Agent',
    hotspot_title: 'AI Agent 商业化提速',
    hotspot_source: 'zhihu',
    hotspot_heat: 256000,
    created_at: '2026-03-30T08:00:00.000Z',
  }

  await page.route(agentApiPattern('/api/v1/agents'), async (route) => {
    await fulfillJson(route, {
      agents: [
        {
          id: 'agent-1',
          name: '热点追踪 Agent',
          is_active: true,
          trigger_rules: {
            sources: ['zhihu'],
            keywords: ['AI Agent'],
            min_heat: 100000,
          },
          platform: 'wechat',
          max_daily: 5,
          today_triggered: 1,
          total_triggered: 12,
        },
      ],
    })
  })

  await page.route(agentApiPattern('/api/v1/agents/drafts'), async (route) => {
    await fulfillJson(route, {
      items: [{ ...draftBase, status: currentDraftStatus }],
      total: 1,
      page: 1,
      limit: 20,
      pages: 1,
    })
  })

  await page.route(agentApiPattern('/api/v1/agents/drafts/draft-review-1/review'), async (route) => {
    reviewRequests += 1
    const payload = route.request().postDataJSON() as { action?: 'accept' | 'discard' }
    reviewAction = payload.action ?? null
    currentDraftStatus = finalDraftStatus
    await fulfillJson(route, { message: 'ok' })
  })

  return {
    getReviewRequests: () => reviewRequests,
    getReviewAction: () => reviewAction,
  }
}

test('C-007: /agent draft accept happy path refreshes mocked reviewed state', async ({ page }) => {
  await mockAuthenticatedMember(page, { membershipTier: 'pro', username: 'agent-review-accept' })
  const reviewState = await mockAgentData(page, 'completed', 'reviewed')

  await page.goto(appUrl('/agent'), { waitUntil: 'domcontentloaded' })
  await page.getByRole('button', { name: '草稿箱' }).click()

  await expect(page.getByText('AI Agent 商业化提速')).toBeVisible()
  await expect(page.getByRole('button', { name: '接受' })).toBeVisible()
  await expect(page.getByRole('button', { name: '丢弃' })).toBeVisible()

  await page.getByRole('button', { name: '接受' }).click()

  await expect.poll(reviewState.getReviewRequests).toBe(1)
  await expect.poll(reviewState.getReviewAction).toBe('accept')
  await expect(page.getByText('已接受草稿')).toBeVisible()
  await expect(page.getByText('已接受', { exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: '接受' })).toHaveCount(0)
  await expect(page.getByRole('button', { name: '丢弃' })).toHaveCount(0)
})

test('C-007: /agent draft discard happy path refreshes mocked discarded state', async ({ page }) => {
  await mockAuthenticatedMember(page, { membershipTier: 'pro', username: 'agent-review-discard' })
  const reviewState = await mockAgentData(page, 'completed', 'discarded')

  await page.goto(appUrl('/agent'), { waitUntil: 'domcontentloaded' })
  await page.getByRole('button', { name: '草稿箱' }).click()

  await expect(page.getByText('AI Agent 商业化提速')).toBeVisible()
  await page.getByRole('button', { name: '丢弃' }).click()

  await expect.poll(reviewState.getReviewRequests).toBe(1)
  await expect.poll(reviewState.getReviewAction).toBe('discard')
  await expect(page.getByText('已丢弃草稿')).toBeVisible()
  await expect(page.getByText('已丢弃', { exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: '接受' })).toHaveCount(0)
  await expect(page.getByRole('button', { name: '丢弃' })).toHaveCount(0)
})
