import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

test('manage script retries compose builds after BuildKit snapshot corruption', () => {
  const source = readFileSync('manage.sh', 'utf8')

  assert.match(source, /failed to prepare extraction snapshot\|parent snapshot \.\* does not exist/)
  assert.match(source, /docker buildx prune -af/)
  assert.match(source, /docker builder prune -af/)
  assert.match(source, /自动清理构建缓存后重试一次/)
})
