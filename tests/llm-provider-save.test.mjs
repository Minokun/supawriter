import test from 'node:test'
import assert from 'node:assert/strict'

import {
  buildLlmProvidersSavePayload,
  mergeProviderModelEdits,
} from '../frontend/src/components/settings/llm-provider-save.js'

test('mergeProviderModelEdits applies edits without mutating original providers', () => {
  const originalProviders = [
    {
      id: 'openai',
      name: 'OpenAI',
      models: [{ name: 'gpt-4', min_tier: 'pro' }],
      api_key: '••••••••',
      enabled: true,
    },
    {
      id: 'deepseek',
      name: 'DeepSeek',
      models: [{ name: 'deepseek-chat', min_tier: 'free' }],
      api_key: '',
      enabled: true,
    },
  ]

  const merged = mergeProviderModelEdits(originalProviders, {
    openai: [{ name: 'gpt-4.1', min_tier: 'ultra' }],
  })

  assert.deepEqual(originalProviders[0].models, [{ name: 'gpt-4', min_tier: 'pro' }])
  assert.deepEqual(merged[0].models, [{ name: 'gpt-4.1', min_tier: 'ultra' }])
  assert.deepEqual(merged[1].models, [{ name: 'deepseek-chat', min_tier: 'free' }])
})

test('buildLlmProvidersSavePayload keeps edited models and omits placeholder api keys', () => {
  const payload = buildLlmProvidersSavePayload(
    [
      {
        id: 'openai',
        name: 'OpenAI',
        models: [{ name: 'gpt-4', min_tier: 'pro' }],
        api_key: '••••••••',
        enabled: true,
      },
    ],
    {
      openai: [{ name: 'gpt-4.1', min_tier: 'ultra' }],
    },
  )

  assert.deepEqual(payload, [
    {
      id: 'openai',
      name: 'OpenAI',
      models: [{ name: 'gpt-4.1', min_tier: 'ultra' }],
      api_key: undefined,
      enabled: true,
    },
  ])
})
