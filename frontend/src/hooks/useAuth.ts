'use client';

import { useState, useEffect, useCallback } from 'react';
import { useSession } from 'next-auth/react';
import { getBackendToken } from '@/lib/api';
import {
  BACKEND_AUTH_CHANGED_EVENT,
  clearBackendAuth,
  getStoredBackendUser,
  hydrateBackendAuthFromCookie,
  persistBackendAuth,
} from '@/lib/backend-auth-storage';
import {
  getStoredAuthToken,
  isClientAuthenticated,
  resolveClientAuthStatus,
} from '@/lib/auth-state';
import { getApiBaseUrl } from '@/lib/api-base-url';
import type { MembershipTier } from '@/types/api';

/**
 * 统一认证 Hook - 优化版本，实现乐观认证
 * 兼容两种登录方式：
 * 1. NextAuth OAuth (Google) — 通过 useSession 获取 session
 * 2. Email/Password — 通过 localStorage 获取 backend JWT token
 *
 * 优化: 如果 localStorage 有 token，立即返回 authenticated 状态，让页面立即渲染
 */

export interface UserInfo {
  id: number;
  username: string;
  email: string;
  display_name?: string;
  avatar?: string;
  bio?: string;
  membership_tier?: MembershipTier;
  is_admin?: boolean;
}

export interface AuthState {
  /** 是否已认证（任一方式） */
  isAuthenticated: boolean;
  /** 认证状态：loading | authenticated | unauthenticated */
  status: 'loading' | 'authenticated' | 'unauthenticated';
  /** 后端 JWT token（用于 API 请求） */
  token: string | null;
  /** NextAuth session（仅 OAuth 登录时有值） */
  session: ReturnType<typeof useSession>['data'];
  /** 获取带认证头的 headers */
  getAuthHeaders: () => Promise<Record<string, string>>;
  /** 用户信息（包含 membership_tier 和 is_admin） */
  userInfo: UserInfo | null;
  /** 用户资料是否已完成解析 */
  profileResolved: boolean;
  /** 是否为管理员 */
  isAdmin: boolean;
  /** 用户会员等级 */
  membershipTier: MembershipTier;
}

export function useAuth(): AuthState {
  const { data: session, status: sessionStatus } = useSession();

  const [token, setToken] = useState<string | null>(null);
  const [localAuthChecked, setLocalAuthChecked] = useState(false);
  const [userInfo, setUserInfo] = useState<UserInfo | null>(null);
  const [profileResolved, setProfileResolved] = useState(true);

  const syncStoredToken = useCallback(() => {
    hydrateBackendAuthFromCookie();
    const storedToken = getStoredAuthToken();
    const nextStoredUser = getStoredBackendUser<Partial<UserInfo>>();
    setToken((currentToken) => (currentToken === storedToken ? currentToken : storedToken));
    if (!storedToken) {
      setUserInfo(null);
      setProfileResolved(true);
    } else if (nextStoredUser?.id && nextStoredUser.username && nextStoredUser.email) {
      setUserInfo({
        id: nextStoredUser.id,
        username: nextStoredUser.username,
        email: nextStoredUser.email,
        display_name: nextStoredUser.display_name,
        avatar: nextStoredUser.avatar,
        bio: nextStoredUser.bio,
        membership_tier: nextStoredUser.membership_tier || 'free',
        is_admin: nextStoredUser.is_admin || false,
      });
      setProfileResolved(true);
    } else {
      setProfileResolved(false);
    }
    setLocalAuthChecked(true);
  }, []);

  // 获取用户信息（包含 tier 和 admin 状态）
  const fetchUserInfo = useCallback(async () => {
    const authToken = token ?? getStoredAuthToken();
    if (!authToken) {
      setUserInfo(null);
      setProfileResolved(true);
      return;
    }

    try {
      setProfileResolved(false);
      const apiBaseUrl = getApiBaseUrl();
      const response = await fetch(`${apiBaseUrl}/api/v1/auth/me`, {
        headers: {
          Authorization: `Bearer ${authToken}`,
          'Content-Type': 'application/json',
        },
      });

      if (response.status === 401 || response.status === 403) {
        clearBackendAuth();
        setToken(null);
        setUserInfo(null);
        setLocalAuthChecked(true);
        setProfileResolved(true);
        return;
      }

      if (!response.ok) {
        throw new Error(`Failed to fetch user info: ${response.status}`);
      }

      const info = await response.json();
      const nextUserInfo = {
        id: info.id,
        username: info.username,
        email: info.email,
        display_name: info.display_name,
        avatar: info.avatar,
        bio: info.bio,
        membership_tier: info.membership_tier as MembershipTier || 'free',
        is_admin: info.is_admin || false,
      };
      setUserInfo(nextUserInfo);
      persistBackendAuth(authToken, nextUserInfo);
      setProfileResolved(true);
    } catch (error) {
      console.error('[useAuth] Failed to fetch user info:', error);
      setProfileResolved(true);
    }
  }, [token]);

  useEffect(() => {
    syncStoredToken();

    if (typeof window === 'undefined') {
      return;
    }

    const handleStorage = (event: StorageEvent) => {
      if (!event.key || event.key === 'token') {
        syncStoredToken();
      }
    };

    window.addEventListener('storage', handleStorage);
    window.addEventListener('focus', syncStoredToken);
    window.addEventListener(BACKEND_AUTH_CHANGED_EVENT, syncStoredToken);

    return () => {
      window.removeEventListener('storage', handleStorage);
      window.removeEventListener('focus', syncStoredToken);
      window.removeEventListener(BACKEND_AUTH_CHANGED_EVENT, syncStoredToken);
    };
  }, [syncStoredToken]);

  // 当认证成功后获取用户信息
  useEffect(() => {
    if (!token) {
      setUserInfo(null);
      setProfileResolved(true);
      return;
    }

    if (localAuthChecked) {
      fetchUserInfo();
    }
  }, [token, localAuthChecked, fetchUserInfo]);

  // 当 NextAuth session 变化时，同步 token 到 localStorage + cookie
  useEffect(() => {
    if (sessionStatus === 'authenticated' && session) {
      // @ts-ignore - accessToken is added by our jwt callback
      const sessionToken = session.accessToken as string | undefined;
      if (sessionToken) {
        // 立即用 session 数据构建 userInfo 乐观更新，避免头像闪烁
        const sessionUserInfo: UserInfo | null = session.user ? {
          // @ts-ignore - id is set by our session callback
          id: Number(session.user.id) || 0,
          username: session.user.email?.split('@')[0] || '',
          email: session.user.email || '',
          display_name: session.user.name || undefined,
          avatar: session.user.image || undefined,
          membership_tier: 'free' as MembershipTier,
          is_admin: false,
        } : null;
        persistBackendAuth(sessionToken, sessionUserInfo);
        setToken(sessionToken);
        if (sessionUserInfo) {
          setUserInfo(sessionUserInfo);
        }
        setLocalAuthChecked(true);
      } else {
        // fallback: 通过 exchange-token API 获取后端 token
        getBackendToken().then((t) => {
          if (t) {
            persistBackendAuth(t);
            setToken(t);
            setLocalAuthChecked(true);
          }
        });
      }
    }
  }, [sessionStatus, session]);

  const resolvedToken = token;
  const isAuthenticated = isClientAuthenticated(sessionStatus, resolvedToken);
  const status = resolveClientAuthStatus(sessionStatus, localAuthChecked, resolvedToken);

  const getAuthHeaders = useCallback(async (): Promise<Record<string, string>> => {
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };

    // 优先使用已有 token
    let authToken = token ?? getStoredAuthToken();
    if (!authToken) {
      authToken = await getBackendToken();
    }

    if (authToken) {
      headers['Authorization'] = `Bearer ${authToken}`;
    }
    return headers;
  }, [token]);

  return {
    isAuthenticated,
    status,
    token: resolvedToken,
    session,
    getAuthHeaders,
    userInfo,
    profileResolved,
    isAdmin: userInfo?.is_admin || false,
    membershipTier: userInfo?.membership_tier || 'free',
  };
}
