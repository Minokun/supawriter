import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

test('backend dockerfile configures a stable pip mirror and uses pip-based installs', () => {
  const source = readFileSync('deployment/Dockerfile.backend', 'utf8')

  assert.match(source, /pip config set global\.index-url https:\/\/pypi\.tuna\.tsinghua\.edu\.cn\/simple/)
  assert.match(source, /pip config set global\.timeout 120/)
  assert.match(source, /RUN pip install -r \/app\/backend\/requirements_api\.txt/)
  assert.match(source, /RUN pip install -r \/app\/requirements\.txt/)
  assert.doesNotMatch(source, /RUN pip install uv/)
  assert.doesNotMatch(source, /uv pip install/)
})
