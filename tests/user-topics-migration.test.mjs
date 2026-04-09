import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync, readdirSync } from 'node:fs'
import { join } from 'node:path'

const versionsDir = join(process.cwd(), 'backend/api/db/migrations/alembic/versions')

test('alembic migrations create the user_topics table', () => {
  const files = readdirSync(versionsDir).filter((file) => file.endsWith('.py'))
  const migrationSources = files.map((file) => readFileSync(join(versionsDir, file), 'utf8'))
  const createsUserTopicsTable = migrationSources.some((source) =>
    /create_table\(\s*['"]user_topics['"]/.test(source),
  )

  assert.equal(
    createsUserTopicsTable,
    true,
    'Expected an Alembic migration to create the user_topics table.',
  )
})
