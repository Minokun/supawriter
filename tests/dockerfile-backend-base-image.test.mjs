import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

test('backend dockerfile pins python slim image to bookworm for stable apt sources', () => {
  const source = readFileSync('deployment/Dockerfile.backend', 'utf8')

  assert.match(source, /^FROM python:3\.12-slim-bookworm AS builder$/m)
  assert.match(source, /^FROM python:3\.12-slim-bookworm AS runner$/m)
  assert.doesNotMatch(source, /^FROM python:3\.12-slim AS /m)
})
