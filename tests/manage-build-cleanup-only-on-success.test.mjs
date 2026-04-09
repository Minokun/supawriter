import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

test('manage script only runs docker cleanup after build commands succeed', () => {
  const source = readFileSync('manage.sh', 'utf8')

  assert.match(source, /if \[ "\$compose_status" -eq 0 \]; then\s+docker_cleanup_after_build\s+rm -f "\$log_file"\s+return 0/s)
  assert.match(source, /if \[ "\$compose_status" -eq 0 \]; then\s+docker_cleanup_after_build\s+fi\s+\s*rm -f "\$log_file"/s)
  assert.match(source, /if \[ "\$requires_build_retry" -eq 0 \]; then\s+docker compose -f "\$COMPOSE_FILE" --env-file "\$DEPLOY_DIR\/\.env" "\$@"/s)
})
