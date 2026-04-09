import test from 'node:test'
import assert from 'node:assert/strict'

import {
  isAdminOnlySettingsTab,
  resolveAccessibleSettingsTab,
} from '../frontend/src/components/settings/admin-tab-access.js'

test('non-admin users cannot remain on admin-only settings tabs', () => {
  assert.equal(isAdminOnlySettingsTab('llm'), true)
  assert.equal(isAdminOnlySettingsTab('services'), true)
  assert.equal(resolveAccessibleSettingsTab('llm', false), 'models')
  assert.equal(resolveAccessibleSettingsTab('services', false), 'models')
})

test('non-admin users keep access to shared settings tabs', () => {
  assert.equal(resolveAccessibleSettingsTab('models', false), 'models')
  assert.equal(resolveAccessibleSettingsTab('preferences', false), 'preferences')
  assert.equal(resolveAccessibleSettingsTab('subscription', false), 'subscription')
})

test('admin users keep access to admin-only tabs', () => {
  assert.equal(resolveAccessibleSettingsTab('llm', true), 'llm')
  assert.equal(resolveAccessibleSettingsTab('services', true), 'services')
})
