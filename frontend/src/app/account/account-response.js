export async function readAccountResponseData(response) {
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    return null
  }

  try {
    return await response.json()
  } catch {
    return null
  }
}

export function getAccountErrorMessage(data, fallbackMessage) {
  if (typeof data?.detail === 'string' && data.detail.trim()) {
    return data.detail
  }

  if (typeof data?.message === 'string' && data.message.trim()) {
    return data.message
  }

  return fallbackMessage
}
