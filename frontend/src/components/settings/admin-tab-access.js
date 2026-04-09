export const ADMIN_ONLY_SETTINGS_TABS = ['llm', 'services']

export function isAdminOnlySettingsTab(tab) {
  return ADMIN_ONLY_SETTINGS_TABS.includes(tab)
}

export function resolveAccessibleSettingsTab(tab, isAdmin) {
  if (!isAdmin && isAdminOnlySettingsTab(tab)) {
    return 'models'
  }

  return tab
}
