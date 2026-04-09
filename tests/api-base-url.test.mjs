import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

test('browser localhost api urls are not forced through the proxy helper', () => {
  const source = readFileSync('frontend/src/lib/api-base-url.ts', 'utf8')

  assert.equal(
    source.includes("['localhost', '127.0.0.1', '0.0.0.0', 'backend']"),
    false,
    'Localhost browser API URLs should be allowed to bypass the Next.js proxy.',
  )
})
