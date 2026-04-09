import { expect, test, type Page, type Route } from '@playwright/test'

const APP_ORIGIN = process.env.PLAYWRIGHT_BASE_URL ?? 'http://127.0.0.1:3001'

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

async function mockAuthenticatedMember(page: Page, options?: { withCookie?: boolean; withStorage?: boolean }) {
  const withCookie = options?.withCookie ?? true
  const withStorage = options?.withStorage ?? true

  await page.context().clearCookies()
  await page.addInitScript(([shouldSeedStorage]) => {
    if (!shouldSeedStorage) {
      return
    }

    window.localStorage.setItem('token', 'regression-member-token')
    window.localStorage.setItem(
      'user',
      JSON.stringify({
        id: 42,
        username: 'regression-member',
        email: 'member@example.com',
        display_name: 'Regression Member',
        membership_tier: 'pro',
        is_admin: false,
      }),
    )
  }, [withStorage])

  if (withCookie) {
    await page.context().addCookies([
      {
        name: 'backend-token',
        value: 'regression-member-token',
        url: APP_ORIGIN,
        httpOnly: false,
        sameSite: 'Lax',
      },
    ])
  }

  await page.route('**/api/auth/session**', async (route) => {
    await fulfillJson(route, null)
  })

  await page.route(apiPattern('/api/v1/auth/me'), async (route) => {
    await fulfillJson(route, {
      id: 42,
      username: 'regression-member',
      email: 'member@example.com',
      display_name: 'Regression Member',
      membership_tier: 'pro',
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

  await page.route('**/api/hotspots/v2/sources**', async (route) => {
    await fulfillJson(route, {
      sources: [
        { id: 'baidu', name: '百度热搜', icon: '🔍', enabled: true },
        { id: 'weibo', name: '微博热搜', icon: '📱', enabled: true },
      ],
    })
  })

  await page.route('**/api/hotspots/v2/latest/baidu**', async (route) => {
    await fulfillJson(route, {
      source: 'baidu',
      updated_at: '2026-03-31T06:00:00.000Z',
      count: 1,
      items: [
        {
          id: 1,
          title: '百度热点示例',
          source: 'baidu',
          rank: 1,
          rank_change: 0,
          is_new: true,
          updated_at: '2026-03-31T06:00:00.000Z',
        },
      ],
    })
  })

  await page.route('**/api/news/**', async (route) => {
    await fulfillJson(route, {
      items: [
        {
          title: '全网热点示例',
          url: 'https://example.com/hotspot',
          hot_score: '12345',
        },
      ],
      cached: false,
    })
  })

  await page.route(apiPattern('/api/v1/articles/'), async (route) => {
    await fulfillJson(route, {
      items: [],
      total: 0,
      page: 1,
      limit: 50,
    })
  })

  await page.route(apiPattern('/api/v1/articles/queue'), async (route) => {
    await fulfillJson(route, {
      items: [],
      total: 0,
    })
  })
}

test('cookie-only sessions recover authenticated navigation before opening history', async ({ page }) => {
  await mockAuthenticatedMember(page, { withCookie: true, withStorage: false })

  await page.goto(appUrl('/pricing'), { waitUntil: 'domcontentloaded' })
  await page.waitForTimeout(1500)

  await expect(page.getByRole('button', { name: /创作中心/ })).toBeVisible()
  await page.goto(appUrl('/history'), { waitUntil: 'domcontentloaded' })

  await expect(page).toHaveURL(/\/history$/)
  await expect(page.getByRole('heading', { name: '历史记录' })).toBeVisible()
})

test('workspace keeps the navigation hub for authenticated users', async ({ page }) => {
  await mockAuthenticatedMember(page)

  await page.goto(appUrl('/workspace'), { waitUntil: 'domcontentloaded' })

  await expect(page).toHaveURL(/\/workspace$/)
  await expect(page.getByRole('heading', { name: '创作空间' })).toBeVisible()
  await expect(page.getByRole('link', { name: /批量生成/ }).first()).toBeVisible()
})

test('creative center menu keeps the batch generation entry', async ({ page }) => {
  await mockAuthenticatedMember(page)

  await page.goto(appUrl('/workspace'), { waitUntil: 'domcontentloaded' })
  await page.getByRole('button', { name: /创作中心/ }).click()

  const creativeMenuBatchLink = page.locator('nav').getByRole('link', { name: '📦 批量生成' })
  await expect(creativeMenuBatchLink).toBeVisible()
  await expect(creativeMenuBatchLink).toHaveAttribute('href', '/batch')
})

test('ai navigator page stays available instead of redirecting to hotspots', async ({ page }) => {
  await mockAuthenticatedMember(page)

  await page.goto(appUrl('/ai-navigator'), { waitUntil: 'domcontentloaded' })

  await expect(page).toHaveURL(/\/ai-navigator$/)
  await expect(page.getByRole('heading', { name: '🚀 内容创作导航中心' })).toBeVisible()
})

test('hotspot info menu restores news and inspiration entries', async ({ page }) => {
  await mockAuthenticatedMember(page)

  await page.goto(appUrl('/workspace'), { waitUntil: 'domcontentloaded' })
  await page.getByRole('button', { name: /热点资讯/ }).click()

  await expect(page.locator('nav').getByRole('link', { name: '🔥 热点中心' })).toBeVisible()
  await expect(page.locator('nav').getByRole('link', { name: '📰 新闻资讯' })).toBeVisible()
  await expect(page.locator('nav').getByRole('link', { name: '💡 全网热点' })).toBeVisible()
})

test('inspiration page stays available for multi-page hotspot navigation', async ({ page }) => {
  await mockAuthenticatedMember(page)

  await page.goto(appUrl('/inspiration'), { waitUntil: 'domcontentloaded' })

  await expect(page).toHaveURL(/\/inspiration$/)
  await expect(page.getByRole('heading', { name: '全网热点' })).toBeVisible()
})

test('hotspots page no longer exposes ops interface details', async ({ page }) => {
  await mockAuthenticatedMember(page)

  await page.goto(appUrl('/hotspots'), { waitUntil: 'domcontentloaded' })

  await expect(page.getByRole('heading', { name: '热点中心' })).toBeVisible()
  await expect(page.getByText('热点资讯分区')).toBeVisible()
  await expect(page.getByText('📡 运维接口')).toHaveCount(0)
  await expect(page.getByText(/localhost:8765|localhost:8000/)).toHaveCount(0)
})
