export async function getSettingsResponseError(response, fallbackMessage) {
  if (response.ok) {
    return null
  }

  try {
    const data = await response.json()

    if (typeof data?.detail === 'string' && data.detail.trim()) {
      return data.detail
    }

    if (typeof data?.message === 'string' && data.message.trim()) {
      return data.message
    }
  } catch {
    // Ignore invalid JSON and fall back to the default message.
  }

  return fallbackMessage
}
