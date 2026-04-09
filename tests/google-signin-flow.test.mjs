import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const readUtf8 = (path) => readFile(new URL(path, import.meta.url), 'utf8')

test('signin page posts Google auth via csrf-backed form submission', async () => {
  const source = await readUtf8('../frontend/src/app/auth/signin/page.tsx')

  assert.match(source, /fetch\('\/api\/auth\/csrf'\)/)
  assert.match(source, /form\.method = 'POST'/)
  assert.match(source, /form\.action = '\/api\/auth\/signin\/google'/)
  assert.match(source, /form\.submit\(\)/)
  assert.doesNotMatch(source, /signIn\('google'/)
})
