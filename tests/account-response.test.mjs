import test from 'node:test'
import assert from 'node:assert/strict'

import {
  getAccountErrorMessage,
  readAccountResponseData,
} from '../frontend/src/app/account/account-response.js'

test('readAccountResponseData returns null for empty successful responses', async () => {
  const response = new Response(null, { status: 204 })

  const data = await readAccountResponseData(response)

  assert.equal(data, null)
})

test('readAccountResponseData parses json responses when present', async () => {
  const response = new Response(JSON.stringify({ detail: '旧密码错误' }), {
    status: 400,
    headers: { 'content-type': 'application/json' },
  })

  const data = await readAccountResponseData(response)

  assert.deepEqual(data, { detail: '旧密码错误' })
})

test('getAccountErrorMessage prefers detail and falls back cleanly', () => {
  assert.equal(getAccountErrorMessage({ detail: '旧密码错误' }, 'fallback'), '旧密码错误')
  assert.equal(getAccountErrorMessage({ message: '请求失败' }, 'fallback'), '请求失败')
  assert.equal(getAccountErrorMessage(null, 'fallback'), 'fallback')
})
