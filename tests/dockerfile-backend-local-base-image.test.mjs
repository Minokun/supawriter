import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

test('local backend dockerfile pins python slim image to bookworm', () => {
  const source = readFileSync('deployment/Dockerfile.backend.local', 'utf8')

  assert.match(source, /^FROM python:3\.12-slim-bookworm$/m)
  assert.doesNotMatch(source, /^FROM python:3\.12-slim$/m)
})
