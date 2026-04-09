import { expect, test, type Page, type Route } from '@playwright/test'

const APP_ORIGIN = process.env.PLAYWRIGHT_BASE_URL ?? 'http://127.0.0.1:3100'

type MembershipTier = 'free' | 'pro' | 'ultra' | 'superuser'

interface MockMemberOptions {
  membershipTier?: MembershipTier
  userId?: number
  username?: string
}

interface DownloadProbeState {
  objectUrls: string[]
  revokedUrls: string[]
  filenames: string[]
  hrefs: string[]
}

function appUrl(pathname: string): string {
  return new URL(pathname, APP_ORIGIN).toString()
}

function batchApiPattern(pathname: string): RegExp {
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

  await page.route(batchApiPattern('/api/v1/auth/me'), async (route) => {
    await fulfillJson(route, {
      id: userId,
      username,
      email: `${username}@supawriter.com`,
      display_name: username,
      membership_tier: membershipTier,
      is_admin: false,
    })
  })

  await page.route(batchApiPattern('/api/v1/alerts/notifications/unread-count'), async (route) => {
    await fulfillJson(route, { count: 0 })
  })

  await page.route(batchApiPattern('/api/v1/settings/models'), async (route) => {
    await fulfillJson(route, {
      chat_model: 'longcat:LongCat-Flash-Chat',
      writer_model: 'longcat:LongCat-Flash-Chat',
    })
  })
}

test('C-006: /batch retry updates drawer state and enables mocked download', async ({ page }) => {
  await mockAuthenticatedMember(page, { membershipTier: 'pro', username: 'batch-retry' })

  let jobsListVersion: 'before-retry' | 'after-retry' = 'before-retry'
  let retryRequests = 0
  let downloadRequests = 0

  const partialJob = {
    id: 'job-retry-1',
    name: '批量重试回归',
    status: 'partial',
    total_count: 2,
    completed_count: 1,
    failed_count: 1,
    progress: 50,
    zip_url: '',
    created_at: '2026-03-29T09:30:00.000Z',
  }

  const completedJob = {
    ...partialJob,
    status: 'completed',
    completed_count: 2,
    failed_count: 0,
    progress: 100,
    zip_url: '/mock/job-retry-1.zip',
  }

  const partialTasks = [
    {
      id: 'task-1',
      topic: '保留成功任务',
      status: 'completed',
      article_id: 'article-1',
    },
    {
      id: 'task-2',
      topic: '等待重试的失败任务',
      status: 'failed',
      error_message: 'mock failure',
    },
  ]

  const completedTasks = [
    {
      id: 'task-1',
      topic: '保留成功任务',
      status: 'completed',
      article_id: 'article-1',
    },
    {
      id: 'task-2',
      topic: '等待重试的失败任务',
      status: 'completed',
      article_id: 'article-2',
    },
  ]

  await page.addInitScript(() => {
    const win = window as typeof window & { __batchDownloadProbe?: DownloadProbeState }
    win.__batchDownloadProbe = {
      objectUrls: [],
      revokedUrls: [],
      filenames: [],
      hrefs: [],
    }

    window.URL.createObjectURL = ((_: Blob | MediaSource) => {
      const url = `blob:mock-batch-download-${win.__batchDownloadProbe!.objectUrls.length + 1}`
      win.__batchDownloadProbe!.objectUrls.push(url)
      return url
    }) as typeof window.URL.createObjectURL

    window.URL.revokeObjectURL = ((url: string) => {
      win.__batchDownloadProbe!.revokedUrls.push(url)
    }) as typeof window.URL.revokeObjectURL

    HTMLAnchorElement.prototype.click = function click(this: HTMLAnchorElement) {
      win.__batchDownloadProbe!.filenames.push(this.download)
      win.__batchDownloadProbe!.hrefs.push(this.href)
    }
  })

  await page.route(batchApiPattern('/api/v1/batch/jobs'), async (route) => {
    await fulfillJson(route, {
      jobs: [jobsListVersion === 'before-retry' ? partialJob : completedJob],
    })
  })

  await page.route(batchApiPattern('/api/v1/batch/jobs/job-retry-1'), async (route) => {
    await fulfillJson(route, {
      job: jobsListVersion === 'before-retry' ? partialJob : completedJob,
      tasks: jobsListVersion === 'before-retry' ? partialTasks : completedTasks,
    })
  })

  await page.route(batchApiPattern('/api/v1/batch/jobs/job-retry-1/retry'), async (route) => {
    retryRequests += 1
    jobsListVersion = 'after-retry'
    await fulfillJson(route, { message: 'ok', retried_count: 1 })
  })

  await page.route(batchApiPattern('/api/v1/batch/jobs/job-retry-1/download'), async (route) => {
    downloadRequests += 1
    await route.fulfill({
      status: 200,
      headers: {
        'content-type': 'application/zip',
      },
      body: 'mock-zip-payload',
    })
  })

  await page.goto(appUrl('/batch'), { waitUntil: 'domcontentloaded' })

  await expect(page.getByRole('heading', { name: '批量重试回归' }).first()).toBeVisible()

  await page.getByRole('button', { name: '查看详情' }).click()
  await expect(page.getByText('等待重试的失败任务')).toBeVisible()
  await expect(page.getByRole('button', { name: '重试失败' })).toBeVisible()
  await expect(page.getByRole('button', { name: '下载全部' })).toHaveCount(0)

  await page.getByRole('button', { name: '重试失败' }).click()

  await expect.poll(() => retryRequests).toBe(1)
  await expect(page.getByText('已重试 1 个任务')).toBeVisible()
  await expect(page.getByRole('button', { name: '下载全部' })).toBeVisible()
  await expect(page.getByRole('button', { name: '重试失败' })).toHaveCount(0)

  await page.getByRole('button', { name: '下载全部' }).click()

  await expect.poll(() => downloadRequests).toBe(1)
  await expect(page.getByText('下载开始')).toBeVisible()

  const downloadProbe = await page.evaluate(() => {
    return (window as typeof window & { __batchDownloadProbe?: DownloadProbeState }).__batchDownloadProbe
  })

  expect(downloadProbe).toEqual({
    objectUrls: ['blob:mock-batch-download-1'],
    revokedUrls: ['blob:mock-batch-download-1'],
    filenames: ['批量重试回归.zip'],
    hrefs: ['blob:mock-batch-download-1'],
  })
})

test('C-006: /batch shows backend detail on first-load failure and recovers after retry', async ({ page }) => {
  await mockAuthenticatedMember(page, { membershipTier: 'pro', username: 'batch-load-error' })

  let shouldFail = true

  await page.route(batchApiPattern('/api/v1/batch/jobs'), async (route) => {
    if (shouldFail) {
      await fulfillJson(route, { detail: '批量任务服务暂不可用' }, 503)
      return
    }

    await fulfillJson(route, { jobs: [] })
  })

  await page.goto(appUrl('/batch'), { waitUntil: 'domcontentloaded' })

  await expect(page.getByRole('heading', { name: '加载批量任务失败' })).toBeVisible()
  await expect(page.locator('main').getByText('批量任务服务暂不可用').first()).toBeVisible()

  shouldFail = false
  await page.getByRole('button', { name: '重新加载' }).click()

  await expect(page.getByRole('heading', { name: '加载批量任务失败' })).toHaveCount(0)
  await expect(page.getByRole('heading', { name: '还没有批量任务' })).toBeVisible()
})
