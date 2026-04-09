import test from 'node:test'
import assert from 'node:assert/strict'

import { resolveUserAvatar } from '../frontend/src/lib/auth-avatar.js'

test('prefers backend avatar when it is present', () => {
  assert.equal(
    resolveUserAvatar({
      backendAvatar: 'https://cdn.example.com/avatar.png',
      sessionAvatar: 'https://lh3.googleusercontent.com/google-avatar=s96-c',
    }),
    'https://cdn.example.com/avatar.png',
  )
})

test('falls back to Google session avatar when backend avatar is missing', () => {
  assert.equal(
    resolveUserAvatar({
      backendAvatar: '   ',
      sessionAvatar: 'https://lh3.googleusercontent.com/google-avatar=s96-c',
    }),
    'https://lh3.googleusercontent.com/google-avatar=s96-c',
  )
})

test('returns null when neither avatar source is usable', () => {
  assert.equal(
    resolveUserAvatar({
      backendAvatar: '',
      sessionAvatar: undefined,
    }),
    null,
  )
})
