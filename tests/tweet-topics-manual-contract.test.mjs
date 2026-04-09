import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

import { normalizeTweetTopicsResponse } from '../frontend/src/lib/tweet-topics-response.js'

const readUtf8 = (path) => readFile(new URL(path, import.meta.url), 'utf8')

test('normalizeTweetTopicsResponse unwraps legacy record payloads', () => {
  const wrapped = {
    record: {
      record_id: 12,
      mode: 'manual',
      news_source: '澎湃科技',
      news_count: 15,
      topics_data: { topics: [] },
    },
  }

  assert.deepEqual(normalizeTweetTopicsResponse(wrapped), wrapped.record)
})

test('normalizeTweetTopicsResponse preserves direct record payloads', () => {
  const direct = {
    record_id: 9,
    mode: 'manual',
    news_source: '实时新闻',
    news_count: 10,
    topics_data: { topics: [{ title: 'A' }] },
  }

  assert.deepEqual(normalizeTweetTopicsResponse(direct), direct)
})

test('manual tweet topics route explicitly demands JSON-only output and returns direct payloads', async () => {
  const source = await readUtf8('../backend/api/routes/tweet_topics.py')

  assert.match(source, /返回JSON格式/)
  assert.match(source, /不要添加任何其他内容/)
  assert.match(source, /return record/)
  assert.doesNotMatch(source, /return\s+\{"record":\s*record\}/)
})

test('tweetTopicsApi normalizes both manual and intelligent generation responses', async () => {
  const source = await readUtf8('../frontend/src/lib/api.ts')

  assert.match(source, /normalizeTweetTopicsResponse\(data\)/)
})
