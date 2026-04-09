const PRIMARY_DESTINATION = '/workspace'

export function resolveAuthDestination(
  callbackUrl: string | null | undefined,
  origin: string
): string {
  if (!callbackUrl) {
    return PRIMARY_DESTINATION
  }

  try {
    const url = callbackUrl.startsWith('/')
      ? new URL(callbackUrl, origin)
      : new URL(callbackUrl)

    if (url.origin !== origin) {
      return PRIMARY_DESTINATION
    }

    if (url.pathname.startsWith('/auth')) {
      return PRIMARY_DESTINATION
    }

    const destination = `${url.pathname}${url.search}${url.hash}`
    return destination || PRIMARY_DESTINATION
  } catch {
    return PRIMARY_DESTINATION
  }
}
