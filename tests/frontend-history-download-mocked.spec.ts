import { expect, test, type Page, type Route } from '@playwright/test'

const APP_ORIGIN = process.env.PLAYWRIGHT_BASE_URL ?? 'http://127.0.0.1:3100'

interface DownloadProbeState {
  objectUrls: string[]
  revokedUrls: string[]
  filenames: string[]
  hrefs: string[]
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

async function mockAuthenticatedMember(page: Page) {
  await page.context().clearCookies()
  await page.addInitScript(() => {
    window.localStorage.setItem('token', 'history-member-token')
    window.localStorage.setItem(
      'user',
      JSON.stringify({
        id: 31,
        username: 'history-member',
        email: 'history@example.com',
        display_name: 'history-member',
        membership_tier: 'pro',
        is_admin: false,
      }),
    )
  })

  await page.context().addCookies([
    {
      name: 'backend-token',
      value: 'history-member-token',
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
      id: 31,
      username: 'history-member',
      email: 'history@example.com',
      display_name: 'History Member',
      membership_tier: 'pro',
      is_admin: false,
    })
  })

  await page.route(apiPattern('/api/v1/alerts/notifications/unread-count'), async (route) => {
    await fulfillJson(route, { count: 0 })
  })
}

test('C-004: /history downloads markdown and html articles with matching extensions', async ({ page }) => {
  await mockAuthenticatedMember(page)

  await page.addInitScript(() => {
    const win = window as typeof window & { __historyDownloadProbe?: DownloadProbeState }
    win.__historyDownloadProbe = {
      objectUrls: [],
      revokedUrls: [],
      filenames: [],
      hrefs: [],
    }

    window.URL.createObjectURL = ((_: Blob | MediaSource) => {
      const url = `blob:mock-history-download-${win.__historyDownloadProbe!.objectUrls.length + 1}`
      win.__historyDownloadProbe!.objectUrls.push(url)
      return url
    }) as typeof window.URL.createObjectURL

    window.URL.revokeObjectURL = ((url: string) => {
      win.__historyDownloadProbe!.revokedUrls.push(url)
    }) as typeof window.URL.revokeObjectURL

    HTMLAnchorElement.prototype.click = function click(this: HTMLAnchorElement) {
      win.__historyDownloadProbe!.filenames.push(this.download)
      win.__historyDownloadProbe!.hrefs.push(this.href)
    }
  })

  await page.route(apiPattern('/api/v1/articles/'), async (route) => {
    await fulfillJson(route, {
      items: [
        {
          id: 'article-md-1',
          topic: 'Markdown 文章',
          title: 'Markdown 文章',
          content: '# markdown body',
          status: 'draft',
          created_at: '2026-03-30T09:00:00.000Z',
          metadata: {},
        },
        {
          id: 'article-html-1',
          topic: 'HTML 文章',
          title: 'HTML 文章',
          content: '<article><h1>html body</h1></article>',
          status: 'published',
          created_at: '2026-03-30T10:00:00.000Z',
          metadata: {},
        },
      ],
      total: 2,
      page: 1,
      limit: 50,
    })
  })

  await page.goto(appUrl('/history'), { waitUntil: 'domcontentloaded' })

  await expect(page.getByText('Markdown 文章')).toBeVisible()
  await expect(page.getByText('HTML 文章')).toBeVisible()

  await page.locator('[data-testid="history-article-article-md-1"] button[title="下载文章"]').click()
  await page.locator('[data-testid="history-article-article-html-1"] button[title="下载文章"]').click()

  const downloadProbe = await page.evaluate(() => {
    return (window as typeof window & { __historyDownloadProbe?: DownloadProbeState }).__historyDownloadProbe
  })

  expect(downloadProbe).toEqual({
    objectUrls: ['blob:mock-history-download-1', 'blob:mock-history-download-2'],
    revokedUrls: ['blob:mock-history-download-1', 'blob:mock-history-download-2'],
    filenames: ['Markdown 文章.md', 'HTML 文章.html'],
    hrefs: ['blob:mock-history-download-1', 'blob:mock-history-download-2'],
  })
})
