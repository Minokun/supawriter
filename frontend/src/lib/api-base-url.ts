function trimTrailingSlash(value: string): string {
  return value.replace(/\/+$/, '');
}

function stripApiSuffix(value: string): string {
  return value.replace(/\/api$/, '');
}

function isProxyPreferredBrowserHost(configuredUrl: string): boolean {
  try {
    const parsed = new URL(configuredUrl);
    return ['backend'].includes(parsed.hostname);
  } catch {
    return false;
  }
}

export function getApiBaseUrl(): string {
  if (typeof window === 'undefined') {
    const internalBaseUrl = process.env.INTERNAL_API_URL;
    if (internalBaseUrl) {
      return trimTrailingSlash(stripApiSuffix(internalBaseUrl));
    }

    const publicBaseUrl = process.env.NEXT_PUBLIC_API_URL;
    if (publicBaseUrl && !publicBaseUrl.startsWith('/')) {
      return trimTrailingSlash(stripApiSuffix(publicBaseUrl));
    }

    return 'http://backend:8000';
  }

  const publicBaseUrl = process.env.NEXT_PUBLIC_API_URL;
  if (!publicBaseUrl) {
    return '/api/backend';
  }

  if (publicBaseUrl.startsWith('/')) {
    return trimTrailingSlash(publicBaseUrl);
  }

  if (isProxyPreferredBrowserHost(publicBaseUrl)) {
    return '/api/backend';
  }

  return trimTrailingSlash(stripApiSuffix(publicBaseUrl));
}
