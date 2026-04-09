'use client';

import { getStoredBackendToken } from '@/lib/backend-auth-storage';

export type SessionStatus = 'authenticated' | 'loading' | 'unauthenticated';
export type ClientAuthStatus = 'authenticated' | 'loading' | 'unauthenticated';

export function getStoredAuthToken(): string | null {
  return getStoredBackendToken();
}

export function hasBackendAuthToken(token?: string | null): boolean {
  return Boolean(token || getStoredAuthToken());
}

export function isClientAuthenticated(
  sessionStatus?: SessionStatus,
  token?: string | null
): boolean {
  return sessionStatus === 'authenticated' || hasBackendAuthToken(token);
}

export function resolveClientAuthStatus(
  sessionStatus: SessionStatus,
  localAuthChecked: boolean,
  token?: string | null
): ClientAuthStatus {
  if (isClientAuthenticated(sessionStatus, token)) {
    return 'authenticated';
  }

  if (sessionStatus === 'loading' || !localAuthChecked) {
    return 'loading';
  }

  return 'unauthenticated';
}
