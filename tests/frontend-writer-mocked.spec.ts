import { expect, test, type Page, type Route } from '@playwright/test'

const APP_ORIGIN = process.env.PLAYWRIGHT_BASE_URL ?? 'http://127.0.0.1:3100'

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

async function mockAuthenticatedMember(page: Page) {
  await page.context().clearCookies()
  await page.addInitScript(() => {
    window.localStorage.setItem('token', 'writer-member-token')
    window.localStorage.setItem(
      'user',
      JSON.stringify({
        id: 17,
        username: 'writer-member',
        email: 'writer@example.com',
        display_name: 'writer-member',
        membership_tier: 'pro',
        is_admin: false,
      }),
    )
  })

  await page.context().addCookies([
    {
      name: 'backend-token',
      value: 'writer-member-token',
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
      id: 17,
      username: 'writer-member',
      email: 'writer@example.com',
      display_name: 'Writer Member',
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
}

test('G-004/G-005: /writer redirects unauthenticated users to signin with a relative callback', async ({ page }) => {
  await page.context().clearCookies()
  await page.goto(appUrl('/writer?articleId=article-17&mode=edit'), { waitUntil: 'domcontentloaded' })

  await expect(page).toHaveURL(/\/auth\/signin\?callbackUrl=%2Fwriter%3FarticleId%3Darticle-17%26mode%3Dedit$/)
})

test('G-009: /writer queue failure shows a retry action and can recover', async ({ page }) => {
  await mockAuthenticatedMember(page)

  let queueRequests = 0

  await page.route(apiPattern('/api/v1/articles/queue'), async (route) => {
    queueRequests += 1
    if (queueRequests < 3) {
      await fulfillJson(route, { detail: 'queue unavailable' }, 503)
      return
    }

    await fulfillJson(route, {
      items: [],
      total: 0,
    })
  })

  await page.goto(appUrl('/writer'), { waitUntil: 'domcontentloaded' })

  await expect(page.getByRole('heading', { name: '任务队列加载失败' })).toBeVisible()
  await expect(page.getByRole('button', { name: '重新加载队列' })).toBeVisible()

  await page.getByRole('button', { name: '重新加载队列' }).click()

  await expect.poll(() => queueRequests).toBeGreaterThanOrEqual(2)
  await expect(page.getByText('当前没有进行中的任务')).toBeVisible()
})

test('G-009: /writer keeps rendered tasks visible when a background queue refresh fails', async ({ page }) => {
  await mockAuthenticatedMember(page)

  let queueRequests = 0

  await page.route(apiPattern('/api/v1/articles/queue'), async (route) => {
    queueRequests += 1

    if (queueRequests === 1) {
      await fulfillJson(route, {
        items: [
          {
            task_id: 'task-running-1',
            topic: 'AI 选题复盘',
            status: 'running',
            progress: 42,
            progress_text: '正在生成',
          },
        ],
        total: 1,
      })
      return
    }

    await fulfillJson(route, { detail: 'temporary queue failure' }, 503)
  })

  await page.goto(appUrl('/writer'), { waitUntil: 'domcontentloaded' })

  await expect(page.getByText('AI 选题复盘')).toBeVisible()
  await expect.poll(() => queueRequests).toBeGreaterThanOrEqual(2, { timeout: 7000 })
  await expect(page.getByText('任务队列刷新失败，当前展示的是最近一次成功加载的数据。')).toBeVisible()
  await expect(page.getByRole('button', { name: '重新加载队列' })).toBeVisible()
  await expect(page.getByText('AI 选题复盘')).toBeVisible()
})

test('C-001: /writer edit mode exposes a visible retry path when article loading fails', async ({ page }) => {
  await mockAuthenticatedMember(page)

  let articleRequests = 0

  await page.route(apiPattern('/api/v1/articles/queue'), async (route) => {
    await fulfillJson(route, {
      items: [],
      total: 0,
    })
  })

  await page.route(apiPattern('/api/v1/articles/detail/article-edit-1'), async (route) => {
    articleRequests += 1
    await fulfillJson(route, { detail: 'article not found' }, 404)
  })

  await page.goto(appUrl('/writer?articleId=article-edit-1&mode=edit'), { waitUntil: 'domcontentloaded' })

  await expect(page.getByRole('heading', { name: '文章加载失败' })).toBeVisible()
  await expect(page.getByText('历史文章加载失败，请稍后重试或返回重新选择文章。')).toBeVisible()

  await page.getByRole('button', { name: '重新加载文章' }).click()

  await expect.poll(() => articleRequests).toBeGreaterThanOrEqual(2)
  await expect(page.getByRole('heading', { name: '文章加载失败' })).toBeVisible()
})
