import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

test('backend default cors config includes the local frontend dev origin', () => {
  const source = readFileSync('backend/api/core/config.py', 'utf8')

  assert.equal(
    source.includes('http://localhost:3001'),
    true,
    'Local frontend dev origin must be allowed by the backend CORS defaults.',
  )
})
