import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const readUtf8 = (path) => readFile(new URL(path, import.meta.url), 'utf8')

test('batch and agent routers are mounted without duplicate path prefixes', async () => {
  const source = await readUtf8('../backend/api/main.py')

  assert.match(
    source,
    /app\.include_router\(batch\.router,\s*prefix="\/api\/v1",\s*tags=\["batch"\]\)/
  )
  assert.match(
    source,
    /app\.include_router\(agent\.router,\s*prefix="\/api\/v1",\s*tags=\["agents"\]\)/
  )
})

test('frontend quota API uses subscription-prefixed backend endpoints', async () => {
  const source = await readUtf8('../frontend/src/lib/api.ts')

  assert.match(source, /\/api\/v1\/subscription\/quota/)
  assert.doesNotMatch(source, /`?\$\{API_URL\}\/api\/v1\/quota(?![-/a-z])/)
  assert.doesNotMatch(source, /`?\$\{API_URL\}\/api\/v1\/quota-packs\/purchase/)
})

test('batch API normalizes backend list and detail payloads for the page layer', async () => {
  const source = await readUtf8('../frontend/src/types/api.ts')

  assert.match(source, /return\s*\{\s*jobs:\s*data\.items\s*\|\|\s*data\.jobs\s*\|\|\s*\[\]\s*\}/s)
  assert.match(source, /job:\s*data\.job\s*\|\|\s*data/s)
  assert.match(source, /tasks:\s*data\.tasks\s*\|\|\s*data\.job\?\.tasks\s*\|\|\s*\[\]/s)
})

test('pricing fallback quota packs use backend-compatible ids', async () => {
  const source = await readUtf8('../frontend/src/app/pricing/page.tsx')

  assert.match(source, /id:\s*'pack_10'/)
  assert.match(source, /id:\s*'pack_50'/)
  assert.doesNotMatch(source, /id:\s*'pack-10'/)
  assert.doesNotMatch(source, /id:\s*'pack-30'/)
})

test('billing client consumes explicit backend subscription semantics', async () => {
  const source = await readUtf8('../frontend/src/lib/api/billing.ts')

  assert.match(source, /feature_tier:\s*string/)
  assert.match(source, /billing_plan\?:\s*string \| null/)
  assert.match(source, /has_active_subscription:\s*boolean/)
  assert.doesNotMatch(source, /const hasActiveSubscription = raw\.current_plan !== 'free' && raw\.status !== 'expired'/)
})
