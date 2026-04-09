import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

test('.dockerignore keeps deployment scripts available to backend image builds', () => {
  const source = readFileSync(' .dockerignore'.trim(), 'utf8')

  assert.match(source, /^deployment\/$/m)
  assert.match(source, /^!deployment\/scripts\/$/m)
  assert.match(source, /^!deployment\/scripts\/\*\*$/m)
})
