import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

test('repair_schema_drift adds the project root to sys.path before importing backend modules', () => {
  const source = readFileSync('deployment/scripts/repair_schema_drift.py', 'utf8')

  assert.match(source, /from pathlib import Path/)
  assert.match(source, /PROJECT_ROOT = Path\(__file__\)\.resolve\(\)\.parents\[2\]/)
  assert.match(source, /sys\.path\.insert\(0, str\(PROJECT_ROOT\)\)/)
  assert.match(source, /from backend\.api\.db\.base import Base/)
})
