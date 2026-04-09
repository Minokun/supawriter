import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

test('manage script cleans dangling docker resources after successful builds', () => {
  const source = readFileSync('manage.sh', 'utf8')

  assert.match(source, /docker_cleanup_after_build\(\)/)
  assert.match(source, /docker image prune -f/)
  assert.match(source, /docker container prune -f/)
  assert.match(source, /docker builder prune -af/)
  assert.match(source, /docker buildx prune -af/)
  assert.match(source, /Conservative cleanup: keep active volumes and running-container logs intact\./)
})
