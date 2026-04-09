/**
 * 统一的 API 客户端
 * 自动处理认证 token 和请求头
 */

import { getSession } from 'next-auth/react';
import { getApiBaseUrl } from './api-base-url';

const API_BASE_URL = getApiBaseUrl();

/**
 * 创建带认证的 fetch 请求
 */
export async function authenticatedFetch(
  endpoint: string,
  options: RequestInit = {}
): Promise<Response> {
  let session = null;
  
  try {
    session = await getSession();
  } catch (error) {
    console.warn('Failed to get session:', error);
  }
  
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };

  // 添加认证 token
  if (session && typeof session === 'object' && 'accessToken' in session && session.accessToken) {
    headers['Authorization'] = `Bearer ${session.accessToken}`;
  }

  // 合并用户提供的 headers
  if (options.headers && typeof options.headers === 'object') {
    Object.assign(headers, options.headers);
  }

  const url = endpoint.startsWith('http') ? endpoint : `${API_BASE_URL}${endpoint}`;

  return fetch(url, {
    ...options,
    headers,
  });
}

/**
 * GET 请求
 */
export async function apiGet<T>(endpoint: string): Promise<T> {
  const response = await authenticatedFetch(endpoint, { method: 'GET' });
  
  if (!response.ok) {
    throw new Error(`API request failed: ${response.status} ${response.statusText}`);
  }
  
  return response.json();
}

/**
 * POST 请求
 */
export async function apiPost<T>(endpoint: string, data?: any): Promise<T> {
  const response = await authenticatedFetch(endpoint, {
    method: 'POST',
    body: data ? JSON.stringify(data) : undefined,
  });
  
  if (!response.ok) {
    throw new Error(`API request failed: ${response.status} ${response.statusText}`);
  }
  
  return response.json();
}

/**
 * PUT 请求
 */
export async function apiPut<T>(endpoint: string, data?: any): Promise<T> {
  const response = await authenticatedFetch(endpoint, {
    method: 'PUT',
    body: data ? JSON.stringify(data) : undefined,
  });
  
  if (!response.ok) {
    throw new Error(`API request failed: ${response.status} ${response.statusText}`);
  }
  
  return response.json();
}

/**
 * DELETE 请求
 */
export async function apiDelete<T>(endpoint: string): Promise<T> {
  const response = await authenticatedFetch(endpoint, { method: 'DELETE' });
  
  if (!response.ok) {
    throw new Error(`API request failed: ${response.status} ${response.statusText}`);
  }
  
  return response.json();
}
