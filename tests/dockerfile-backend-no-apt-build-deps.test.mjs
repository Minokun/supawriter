import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

test('backend dockerfile does not depend on apt build tools during image build', () => {
  const source = readFileSync('deployment/Dockerfile.backend', 'utf8')

  assert.doesNotMatch(source, /apt-get update/)
  assert.doesNotMatch(source, /apt-get install/)
  assert.doesNotMatch(source, /RUN pip install uv/)
  assert.doesNotMatch(source, /uv pip install/)
  assert.match(source, /RUN pip install -r \/app\/backend\/requirements_api\.txt/)
  assert.match(source, /RUN pip install -r \/app\/requirements\.txt/)
})
