import test from 'node:test'
import assert from 'node:assert/strict'

import { getSettingsResponseError } from '../frontend/src/components/settings/settings-response.js'

test('returns null for successful settings responses', async () => {
  const response = new Response(JSON.stringify({ ok: true }), {
    status: 200,
    headers: { 'content-type': 'application/json' },
  })

  const message = await getSettingsResponseError(response, 'fallback')

  assert.equal(message, null)
})

test('prefers detail from failed settings responses', async () => {
  const response = new Response(JSON.stringify({ detail: '需要管理员权限' }), {
    status: 403,
    headers: { 'content-type': 'application/json' },
  })

  const message = await getSettingsResponseError(response, 'fallback')

  assert.equal(message, '需要管理员权限')
})

test('falls back when failed settings responses are not valid JSON', async () => {
  const response = new Response('server exploded', {
    status: 500,
    headers: { 'content-type': 'text/plain' },
  })

  const message = await getSettingsResponseError(response, '操作失败，请重试')

  assert.equal(message, '操作失败，请重试')
})

test('falls back to message when detail is absent', async () => {
  const response = new Response(JSON.stringify({ message: '提供商配置不合法' }), {
    status: 422,
    headers: { 'content-type': 'application/json' },
  })

  const message = await getSettingsResponseError(response, 'fallback')

  assert.equal(message, '提供商配置不合法')
})
