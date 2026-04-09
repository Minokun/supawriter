import test from 'node:test'
import assert from 'node:assert/strict'
import { execFileSync } from 'node:child_process'
import { readFileSync } from 'node:fs'

test('tracked env files are not committed', () => {
  const tracked = execFileSync('git', ['ls-files'], { encoding: 'utf8' })
    .split('\n')
    .filter(Boolean)

  const trackedLiveEnvFiles = tracked.filter((file) => {
    const basename = file.split('/').at(-1) ?? ''
    const isEnvFile = basename.startsWith('.env')
    const isExampleFile = file.endsWith('.example')
    return isEnvFile && !isExampleFile
  })

  assert.deepEqual(trackedLiveEnvFiles, [])
})

test('example env files keep placeholders instead of live secrets', () => {
  const rootExample = readFileSync('.env.example', 'utf8')
  const deployExample = readFileSync('deployment/.env.example', 'utf8')

  assert.match(rootExample, /GOOGLE_CLIENT_ID=your_google_client_id/i)
  assert.match(deployExample, /JWT_SECRET_KEY=CHANGE_ME_TO_A_LONG_RANDOM_VALUE/)
  assert.doesNotMatch(rootExample, /JWT_SECRET_KEY=ipYnDiOOM/i)
  assert.doesNotMatch(deployExample, /ENCRYPTION_KEY=Txnojiw-/i)
})
