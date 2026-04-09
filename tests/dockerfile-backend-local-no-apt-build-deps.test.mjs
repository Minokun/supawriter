import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

test('local backend dockerfile does not install apt build dependencies', () => {
  const source = readFileSync('deployment/Dockerfile.backend.local', 'utf8')

  assert.doesNotMatch(source, /apt-get update/)
  assert.doesNotMatch(source, /\bgcc\b/)
  assert.doesNotMatch(source, /\bg\+\+\b/)
  assert.doesNotMatch(source, /\bcurl\b/)
})
