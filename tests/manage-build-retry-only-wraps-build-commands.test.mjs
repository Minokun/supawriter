import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

test('manage script only enables snapshot recovery for build-related compose commands', () => {
  const source = readFileSync('manage.sh', 'utf8')

  assert.match(source, /if \[ "\$arg" = "build" \] \|\| \[ "\$arg" = "--build" \]/)
  assert.match(source, /if \[ "\$requires_build_retry" -eq 0 \]; then/)
  assert.match(source, /docker compose -f "\$COMPOSE_FILE" --env-file "\$DEPLOY_DIR\/\.env" "\$@"/)
})
