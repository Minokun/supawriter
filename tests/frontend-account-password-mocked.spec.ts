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

async function mockAuthenticatedAccount(page: Page) {
  await page.context().clearCookies()
  await page.addInitScript(() => {
    window.localStorage.setItem('token', 'account-member-token')
    window.localStorage.setItem(
      'user',
      JSON.stringify({
        id: 23,
        username: 'account-member',
        email: 'account@example.com',
        display_name: 'account-member',
        membership_tier: 'pro',
        is_admin: false,
      }),
    )
  })

  await page.context().addCookies([
    {
      name: 'backend-token',
      value: 'account-member-token',
      url: APP_ORIGIN,
      httpOnly: false,
      sameSite: 'Lax',
    },
  ])

  await page.route('**/api/auth/session**', async (route) => {
    await fulfillJson(route, {})
  })

  await page.route(apiPattern('/api/v1/auth/profile'), async (route) => {
    await fulfillJson(route, {
      id: 23,
      username: 'account-member',
      email: 'account@example.com',
      display_name: 'Account Member',
      has_password: true,
      oauth_accounts: [],
    })
  })
}

test('A-007: /account change password success closes form and resets fields', async ({ page }) => {
  await mockAuthenticatedAccount(page)

  let changePasswordRequests = 0

  await page.route(apiPattern('/api/v1/auth/change-password'), async (route) => {
    changePasswordRequests += 1
    await fulfillJson(route, { message: 'ok' })
  })

  await page.goto(appUrl('/account'), { waitUntil: 'domcontentloaded', timeout: 60000 })

  await page.getByRole('button', { name: '修改密码' }).click()
  await page.getByPlaceholder('输入当前密码').fill('old-password-123')
  await page.getByPlaceholder('至少 8 个字符').fill('new-password-456')
  await page.getByPlaceholder('再次输入新密码').fill('new-password-456')
  await page.getByRole('button', { name: '确认修改' }).click()

  await expect.poll(() => changePasswordRequests).toBe(1)
  await expect(page.getByText('密码修改成功')).toBeVisible()
  await expect(page.getByRole('heading', { name: '修改密码' })).toHaveCount(0)
})

test('A-007: /account change password failure keeps form open and shows backend error', async ({ page }) => {
  await mockAuthenticatedAccount(page)

  let changePasswordRequests = 0

  await page.route(apiPattern('/api/v1/auth/change-password'), async (route) => {
    changePasswordRequests += 1
    await fulfillJson(route, { detail: '旧密码不正确' }, 400)
  })

  await page.goto(appUrl('/account'), { waitUntil: 'domcontentloaded', timeout: 60000 })

  await page.getByRole('button', { name: '修改密码' }).click()
  await page.getByPlaceholder('输入当前密码').fill('wrong-old-password')
  await page.getByPlaceholder('至少 8 个字符').fill('new-password-456')
  await page.getByPlaceholder('再次输入新密码').fill('new-password-456')
  await page.getByRole('button', { name: '确认修改' }).click()

  await expect.poll(() => changePasswordRequests).toBe(1)
  await expect(page.getByText('旧密码不正确')).toBeVisible()
  await expect(page.getByRole('heading', { name: '修改密码' })).toBeVisible()
  await expect(page.getByPlaceholder('输入当前密码')).toHaveValue('wrong-old-password')
})

test('A-007: /account expires auth and redirects to signin when profile loading returns 401', async ({ page }) => {
  await page.context().clearCookies()
  await page.addInitScript(() => {
    window.localStorage.setItem('token', 'expired-account-token')
    window.localStorage.setItem(
      'user',
      JSON.stringify({
        id: 23,
        username: 'expired-account',
        email: 'expired@example.com',
        display_name: 'expired-account',
        membership_tier: 'pro',
        is_admin: false,
      }),
    )
  })

  await page.context().addCookies([
    {
      name: 'backend-token',
      value: 'expired-account-token',
      url: APP_ORIGIN,
      httpOnly: false,
      sameSite: 'Lax',
    },
  ])

  await page.route('**/api/auth/session**', async (route) => {
    await fulfillJson(route, {})
  })

  await page.route(apiPattern('/api/v1/auth/profile'), async (route) => {
    await fulfillJson(route, { detail: 'token expired' }, 401)
  })

  await page.goto(appUrl('/account'), { waitUntil: 'domcontentloaded', timeout: 60000 })

  await expect(page).toHaveURL(/\/auth\/signin\?callbackUrl=%2Faccount$/)
})
