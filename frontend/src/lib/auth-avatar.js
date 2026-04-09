function normalizeAvatar(value) {
  if (typeof value !== 'string') {
    return null
  }

  const trimmed = value.trim()
  return trimmed.length > 0 ? trimmed : null
}

export function resolveUserAvatar({ backendAvatar, sessionAvatar }) {
  return normalizeAvatar(backendAvatar) ?? normalizeAvatar(sessionAvatar) ?? null
}
