const isBrowser = () => typeof window !== 'undefined';

interface CacheEnvelope<T> {
  data: T;
  timestamp: number;
}

export function getSessionCache<T>(key: string, ttlMs: number): T | null {
  if (!isBrowser()) return null;

  try {
    const raw = sessionStorage.getItem(key);
    if (!raw) return null;

    const parsed = JSON.parse(raw) as CacheEnvelope<T>;
    if (!parsed || typeof parsed.timestamp !== 'number') {
      sessionStorage.removeItem(key);
      return null;
    }

    if (Date.now() - parsed.timestamp > ttlMs) {
      sessionStorage.removeItem(key);
      return null;
    }

    return parsed.data;
  } catch {
    return null;
  }
}

export function setSessionCache<T>(key: string, data: T): void {
  if (!isBrowser()) return;

  try {
    const payload: CacheEnvelope<T> = {
      data,
      timestamp: Date.now(),
    };
    sessionStorage.setItem(key, JSON.stringify(payload));
  } catch {}
}

export function removeSessionCache(key: string): void {
  if (!isBrowser()) return;
  sessionStorage.removeItem(key);
}
