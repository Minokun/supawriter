import { expect, test, type Page, type Route } from '@playwright/test'

const APP_ORIGIN = process.env.PLAYWRIGHT_BASE_URL ?? 'http://127.0.0.1:3100'

type MembershipTier = 'free' | 'pro' | 'ultra' | 'superuser'

interface MockSettingsUserOptions {
  isAdmin?: boolean
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

async function mockAuthenticatedSettingsUser(page: Page, options: MockSettingsUserOptions = {}) {
  const isAdmin = options.isAdmin ?? false
  const membershipTier = options.membershipTier ?? (isAdmin ? 'superuser' : 'pro')
  const userId = options.userId ?? (isAdmin ? 1 : 88)
  const username = options.username ?? (isAdmin ? 'settings-admin' : 'settings-member')
  const token = `${username}-token`

  await page.context().clearCookies()
  await page.addInitScript(
    ([authToken, id, name, tier, admin]) => {
      window.localStorage.setItem('token', authToken)
      window.localStorage.setItem(
        'user',
        JSON.stringify({
          id,
          username: name,
          email: `${name}@supawriter.com`,
          display_name: name,
          membership_tier: tier,
          is_admin: admin,
        }),
      )
    },
    [token, userId, username, membershipTier, isAdmin],
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
      is_admin: isAdmin,
    })
  })

  await page.route(apiPattern('/api/v1/alerts/notifications/unread-count'), async (route) => {
    await fulfillJson(route, { count: 0 })
  })
}

const memberProviders = [
  {
    id: 'deepseek',
    name: 'DeepSeek',
    models: [{ name: 'deepseek-chat', min_tier: 'free' }],
    base_url: 'https://api.deepseek.com/v1',
    api_key: '••••••••',
    enabled: true,
  },
]

const adminProviders = [
  {
    id: 'openai',
    name: 'OpenAI',
    models: [{ name: 'gpt-4.1', min_tier: 'pro' }],
    base_url: 'https://api.openai.com/v1',
    api_key: '••••••••',
    enabled: true,
  },
]

test('A-008: /settings hides admin-only tabs for non-admin members', async ({ page }) => {
  await mockAuthenticatedSettingsUser(page)

  await page.route(apiPattern('/api/v1/settings/llm-provider-templates'), async (route) => {
    await fulfillJson(route, { templates: [] })
  })

  await page.route(apiPattern('/api/v1/settings/available-providers'), async (route) => {
    await fulfillJson(route, { providers: memberProviders })
  })

  await page.route(apiPattern('/api/v1/settings/models'), async (route) => {
    await fulfillJson(route, {
      chat_model: 'deepseek:deepseek-chat',
      writer_model: 'deepseek:deepseek-chat',
    })
  })

  await page.goto(appUrl('/settings'), { waitUntil: 'domcontentloaded' })

  await expect(page.getByRole('button', { name: '模型配置', exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: '个人偏好', exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: 'LLM 提供商' })).toHaveCount(0)
  await expect(page.getByRole('button', { name: '其他服务' })).toHaveCount(0)
})

test('A-008: /settings shows a visible first-load error card and retries successfully', async ({ page }) => {
  await mockAuthenticatedSettingsUser(page)

  let shouldFailModelsLoad = true

  await page.route(apiPattern('/api/v1/settings/llm-provider-templates'), async (route) => {
    await fulfillJson(route, { templates: [] })
  })

  await page.route(apiPattern('/api/v1/settings/available-providers'), async (route) => {
    await fulfillJson(route, { providers: memberProviders })
  })

  await page.route(apiPattern('/api/v1/settings/models'), async (route) => {
    if (shouldFailModelsLoad) {
      await fulfillJson(route, { detail: 'settings models unavailable' }, 500)
      return
    }

    await fulfillJson(route, {
      chat_model: 'deepseek:deepseek-chat',
      writer_model: 'deepseek:deepseek-chat',
    })
  })

  await page.goto(appUrl('/settings'), { waitUntil: 'domcontentloaded' })

  await expect(page.getByRole('heading', { name: '系统设置加载失败' })).toBeVisible()
  await expect(page.getByText('settings models unavailable')).toBeVisible()

  shouldFailModelsLoad = false
  await page.getByRole('button', { name: '重新加载' }).click()

  await expect(page.getByRole('heading', { name: '系统设置加载失败' })).toHaveCount(0)
  await expect(page.getByRole('heading', { name: 'Chat 模型' })).toBeVisible()
})

test('A-008: /settings models save shows backend detail instead of a generic error', async ({ page }) => {
  await mockAuthenticatedSettingsUser(page)

  let saveRequests = 0

  await page.route(apiPattern('/api/v1/settings/llm-provider-templates'), async (route) => {
    await fulfillJson(route, { templates: [] })
  })

  await page.route(apiPattern('/api/v1/settings/available-providers'), async (route) => {
    await fulfillJson(route, { providers: memberProviders })
  })

  await page.route(apiPattern('/api/v1/settings/models'), async (route) => {
    if (route.request().method() === 'PUT') {
      saveRequests += 1
      await fulfillJson(route, { detail: '默认模型不可用' }, 422)
      return
    }

    await fulfillJson(route, {
      chat_model: 'deepseek:deepseek-chat',
      writer_model: 'deepseek:deepseek-chat',
    })
  })

  await page.goto(appUrl('/settings'), { waitUntil: 'domcontentloaded' })
  await page.getByRole('button', { name: '保存模型配置' }).click()

  await expect.poll(() => saveRequests).toBe(1)
  await expect(page.getByText('默认模型不可用')).toBeVisible()
})

test('A-008: /settings preferences save shows backend message detail', async ({ page }) => {
  await mockAuthenticatedSettingsUser(page)

  let saveRequests = 0

  await page.route(apiPattern('/api/v1/settings/llm-provider-templates'), async (route) => {
    await fulfillJson(route, { templates: [] })
  })

  await page.route(apiPattern('/api/v1/settings/available-providers'), async (route) => {
    await fulfillJson(route, { providers: memberProviders })
  })

  await page.route(apiPattern('/api/v1/settings/models'), async (route) => {
    await fulfillJson(route, {
      chat_model: 'deepseek:deepseek-chat',
      writer_model: 'deepseek:deepseek-chat',
    })
  })

  await page.route(apiPattern('/api/v1/settings/preferences'), async (route) => {
    if (route.request().method() === 'PUT') {
      saveRequests += 1
      await fulfillJson(route, { message: '语言设置无效' }, 422)
      return
    }

    await fulfillJson(route, {
      editor_theme: 'light',
      language: 'zh-CN',
      auto_save: true,
      notifications_enabled: true,
    })
  })

  await page.goto(appUrl('/settings'), { waitUntil: 'domcontentloaded' })
  await page.getByRole('button', { name: '个人偏好', exact: true }).click()
  await expect(page.getByRole('button', { name: '保存偏好设置' })).toBeVisible()

  await page.getByRole('button', { name: '保存偏好设置' }).click()

  await expect.poll(() => saveRequests).toBe(1)
  await expect(page.getByText('语言设置无效')).toBeVisible()
})

test('A-008: /settings admin provider add surfaces backend errors to the user', async ({ page }) => {
  await mockAuthenticatedSettingsUser(page, { isAdmin: true, username: 'settings-admin-add' })

  let addRequests = 0

  await page.route(apiPattern('/api/v1/settings/llm-provider-templates'), async (route) => {
    await fulfillJson(route, {
      templates: [
        {
          id: 'anthropic',
          name: 'Anthropic',
          base_url: 'https://api.anthropic.com/v1',
          default_models: ['claude-3-7-sonnet'],
          category: 'text',
          description: 'Anthropic Claude models',
          requires_api_key: true,
        },
      ],
    })
  })

  await page.route(apiPattern('/api/v1/settings/llm-providers'), async (route) => {
    if (route.request().method() === 'PUT') {
      addRequests += 1
      await fulfillJson(route, { detail: 'Anthropic 提供商配置校验失败' }, 400)
      return
    }

    await fulfillJson(route, { providers: adminProviders })
  })

  await page.route(apiPattern('/api/v1/settings/models'), async (route) => {
    await fulfillJson(route, {
      chat_model: 'openai:gpt-4.1',
      writer_model: 'openai:gpt-4.1',
    })
  })

  await page.goto(appUrl('/settings'), { waitUntil: 'domcontentloaded' })
  await page.getByRole('button', { name: 'LLM 提供商' }).click()
  await expect(page.getByRole('button', { name: '添加提供商' })).toBeVisible()

  await page.getByRole('button', { name: '添加提供商' }).click()
  await page.getByRole('heading', { name: 'Anthropic' }).click()

  await expect.poll(() => addRequests).toBe(1)
  await expect(page.getByText('Anthropic 提供商配置校验失败')).toBeVisible()
  await expect(page.getByText('添加 LLM 提供商')).toBeVisible()
})

test('A-008: /settings services save surfaces backend errors to the user', async ({ page }) => {
  await mockAuthenticatedSettingsUser(page, { isAdmin: true, username: 'settings-admin-services' })

  let serviceSaveRequests = 0

  await page.route(apiPattern('/api/v1/settings/llm-provider-templates'), async (route) => {
    await fulfillJson(route, { templates: [] })
  })

  await page.route(apiPattern('/api/v1/settings/llm-providers'), async (route) => {
    await fulfillJson(route, { providers: adminProviders })
  })

  await page.route(apiPattern('/api/v1/settings/models'), async (route) => {
    await fulfillJson(route, {
      chat_model: 'openai:gpt-4.1',
      writer_model: 'openai:gpt-4.1',
    })
  })

  await page.route(apiPattern('/api/v1/settings/services'), async (route) => {
    if (route.request().method() === 'PUT') {
      serviceSaveRequests += 1
      await fulfillJson(route, { detail: '七牛 Bucket 不存在' }, 400)
      return
    }

    await fulfillJson(route, {
      qiniu_domain: 'https://cdn.example.com',
      qiniu_folder: 'supawriter/',
      qiniu_bucket: 'demo-bucket',
      qiniu_access_key: 'masked-ak',
      qiniu_secret_key: 'masked-sk',
      qiniu_region: 'z2',
      qiniu_key_set: true,
      serper_api_key: 'masked-serper',
      serper_key_set: true,
    })
  })

  await page.goto(appUrl('/settings'), { waitUntil: 'domcontentloaded' })
  await page.getByRole('button', { name: '其他服务' }).click()
  await expect(page.getByRole('button', { name: '保存七牛云配置' })).toBeVisible()

  await page.getByRole('button', { name: '保存七牛云配置' }).click()

  await expect.poll(() => serviceSaveRequests).toBe(1)
  await expect(page.getByText('七牛 Bucket 不存在')).toBeVisible()
})
