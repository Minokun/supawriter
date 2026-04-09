const TOKEN_KEY = 'token';
const USER_KEY = 'user';
const COOKIE_KEY = 'backend-token';
export const BACKEND_AUTH_CHANGED_EVENT = 'backend-auth-changed';

function notifyBackendAuthChanged() {
  if (typeof window === 'undefined') return;
  window.dispatchEvent(new Event(BACKEND_AUTH_CHANGED_EVENT));
}

function readCookieToken(cookieString: string, key: string): string | null {
  const prefix = `${key}=`;
  const match = cookieString
    .split(';')
    .map((item) => item.trim())
    .find((item) => item.startsWith(prefix));

  if (!match) {
    return null;
  }

  const value = match.slice(prefix.length);
  return value ? decodeURIComponent(value) : null;
}

function writeBackendCookie(token: string) {
  document.cookie = `${COOKIE_KEY}=${encodeURIComponent(token)}; path=/; max-age=${30 * 24 * 3600}; SameSite=Lax`;
}

export function getStoredBackendToken(): string | null {
  if (typeof window === 'undefined') return null;

  const localToken = localStorage.getItem(TOKEN_KEY);
  const cookieToken = readCookieToken(document.cookie, COOKIE_KEY);

  if (localToken) {
    if (cookieToken !== localToken) {
      writeBackendCookie(localToken);
    }
    return localToken;
  }

  if (cookieToken) {
    localStorage.setItem(TOKEN_KEY, cookieToken);
    return cookieToken;
  }

  return null;
}

export function hydrateBackendAuthFromCookie(): string | null {
  if (typeof window === 'undefined') return null;

  const cookieToken = readCookieToken(document.cookie, COOKIE_KEY);
  if (!cookieToken) {
    return null;
  }

  if (localStorage.getItem(TOKEN_KEY) !== cookieToken) {
    localStorage.setItem(TOKEN_KEY, cookieToken);
  }

  return cookieToken;
}

export function getStoredBackendUser<T = unknown>(): T | null {
  if (typeof window === 'undefined') return null;
  const raw = localStorage.getItem(USER_KEY);
  if (!raw) return null;

  try {
    return JSON.parse(raw) as T;
  } catch {
    localStorage.removeItem(USER_KEY);
    return null;
  }
}

export function persistBackendAuth(token: string, user?: unknown) {
  if (typeof window === 'undefined') return;
  localStorage.setItem(TOKEN_KEY, token);
  if (user !== undefined) {
    localStorage.setItem(USER_KEY, JSON.stringify(user));
  }
  writeBackendCookie(token);
  notifyBackendAuthChanged();
}

export function clearBackendAuth() {
  if (typeof window === 'undefined') return;
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);

  const cookieStoreApi = (window as typeof window & {
    cookieStore?: {
      delete: (options: { name: string; path?: string; domain?: string }) => Promise<void>;
    };
  }).cookieStore;

  const hostname = window.location.hostname;

  if (cookieStoreApi) {
    for (const domain of [undefined, hostname, `.${hostname}`]) {
      cookieStoreApi.delete({ name: 'backend-token', path: '/', domain }).catch(() => {});
    }
  }

  for (const domainVariant of ['', `; domain=${hostname}`, `; domain=.${hostname}`]) {
    document.cookie = `backend-token=; path=/; max-age=0; expires=Thu, 01 Jan 1970 00:00:00 GMT; SameSite=Lax${domainVariant}`;
  }

  notifyBackendAuthChanged();
}
