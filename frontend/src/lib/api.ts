import axios from 'axios';
import { getApiBaseUrl } from './api-base-url';
import { normalizeTweetTopicsResponse } from './tweet-topics-response.js';

const API_BASE_URL = getApiBaseUrl();

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 长超时时间 API 实例（用于耗时较长的操作，如推文选题生成）
const longTimeoutApi = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120000, // 2分钟超时
  headers: {
    'Content-Type': 'application/json',
  },
});

// 为 longTimeoutApi 添加相同的拦截器
const addInterceptors = (axiosInstance: typeof api) => {
  axiosInstance.interceptors.request.use(
    (config) => {
      const token = localStorage.getItem('token');
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    },
    (error) => {
      return Promise.reject(error);
    }
  );

  axiosInstance.interceptors.response.use(
    (response) => response.data,
    async (error) => {
      if (error.response?.status === 401) {
        // 避免循环重试 - 检查是否已经在重试中
        if (!error.config._retry) {
          error.config._retry = true;
          // 强制刷新 token（清除旧 token，从 session 获取新 token）
          const newToken = await getBackendToken(true);
          if (newToken) {
            // Retry the original request with new token
            const originalRequest = error.config;
            originalRequest.headers.Authorization = `Bearer ${newToken}`;
            return axiosInstance(originalRequest);
          }
        }
        // 无法获取新 token，清除本地数据并跳转到登录页
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        window.location.href = '/auth/signin';
      }
      return Promise.reject(error);
    }
  );
};

// 为两个 API 实例添加拦截器
addInterceptors(api);
addInterceptors(longTimeoutApi);

export default api;

// =============================================================================
// 认证 API (Token Exchange)
// =============================================================================

export interface BackendTokenResponse {
  access_token: string;
  token_type: string;
  user: {
    id: number;
    username: string;
    email: string;
    display_name?: string;
    avatar?: string;
    bio?: string;
  };
}

let tokenPromise: Promise<string | null> | null = null;

/**
 * Get backend JWT token from NextAuth session
 * This exchanges the frontend OAuth session for a backend JWT token
 */
export async function getBackendToken(forceRefresh: boolean = false): Promise<string | null> {
  // Prevent multiple concurrent token requests
  if (tokenPromise) {
    console.log('[getBackendToken] Returning existing token promise');
    return tokenPromise;
  }

  tokenPromise = (async () => {
    try {
      // First check if we have a valid token in localStorage
      const existingToken = localStorage.getItem('token');
      console.log('[getBackendToken] Existing token in localStorage:', existingToken ? `${existingToken.substring(0, 20)}...` : 'null');
      
      if (existingToken && !forceRefresh) {
        // 如果有现有 token 且不强制刷新，直接返回
        console.log('[getBackendToken] Using cached token');
        return existingToken;
      }

      // Exchange NextAuth session for backend token
      console.log('[getBackendToken] Exchanging NextAuth session for backend token...');
      const response = await fetch('/api/auth/backend-token', {
        method: 'POST',
      });

      console.log('[getBackendToken] Backend token exchange response status:', response.status);

      if (!response.ok) {
        if (response.status === 401) {
          // 没有有效的 NextAuth session
          // 如果有现有 token（邮箱登录），保留它而不是清除
          if (existingToken) {
            console.log('[getBackendToken] No NextAuth session, keeping existing email-login token');
            return existingToken;
          }
          console.warn('[getBackendToken] No valid session found');
        } else {
          const errorText = await response.text();
          console.error('[getBackendToken] Failed to get backend token:', errorText);
        }
        return null;
      }

      const data = await response.json() as BackendTokenResponse;
      console.log('[getBackendToken] Token exchange successful, user:', data.user?.email);

      // Store the token in localStorage
      localStorage.setItem('token', data.access_token);
      localStorage.setItem('user', JSON.stringify(data.user));

      return data.access_token;
    } catch (error) {
      console.error('[getBackendToken] Error getting backend token:', error);
      return null;
    } finally {
      tokenPromise = null;
    }
  })();

  return tokenPromise;
}

/**
 * Ensure we have a valid backend token before making API calls
 * Call this before using any backend API that requires authentication
 */
export async function ensureAuth(): Promise<boolean> {
  const token = await getBackendToken();
  return token !== null;
}

// =============================================================================
// 聊天 API
// =============================================================================

export interface ChatMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp?: string;
}

export interface ChatSession {
  id: string;
  user_id: number;
  title: string;
  model?: string;
  messages: ChatMessage[];
  created_at: string;
  updated_at: string;
}

export interface ChatSendRequest {
  session_id?: string;
  message: string;
  model?: string;
  enable_search?: boolean;
}

export interface ChatSendResponse {
  type: 'user_message' | 'assistant_chunk' | 'assistant_thinking' | 'assistant_end' | 'error' | 'search_start' | 'search_progress' | 'search_complete' | 'search_error';
  session_id: string;
  text?: string;
  thinking?: string;
  full_text?: string;
  is_end?: boolean;
  message?: string;
  search_data?: SearchResult[];
  results?: SearchResult[];
}

// =============================================================================
// 搜索相关类型
// =============================================================================

export interface SearchResult {
  title: string;
  url: string;
  snippet: string;
  source?: string;
  body?: string;
  score?: number;
  images?: string[];
}

export interface SearchStats {
  original_query: string;
  optimized_query: string;
  ddgs_count: number;
  serper_count: number;
  total_before_llm_filter: number;
  total_after_llm_filter: number;
  total_after_dedup: number;
  final_count: number;
  web_images_count: number;
  total_images_count: number;
}

/**
 * 发送聊天消息（SSE 流式响应）
 */
export async function sendChatMessage(
  data: ChatSendRequest,
  onChunk: (chunk: ChatSendResponse) => void,
  onComplete?: () => void,
  onError?: (error: Error) => void
): Promise<void> {
  const token = localStorage.getItem('token');
  const url = `${API_BASE_URL}/api/v1/chat/send`;

  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify(data),
      // 确保不缓存流式响应
      cache: 'no-store',
    });

    if (!response.ok) {
      console.error('[API] Response not OK:', response.status);
      // 尝试读取错误详情
      try {
        const errorData = await response.json();
        const errorMessage = errorData.detail || errorData.message || `HTTP error! status: ${response.status}`;
        throw new Error(errorMessage);
      } catch (parseError) {
        // 如果无法解析 JSON，使用默认错误信息
        throw new Error(`HTTP error! status: ${response.status}`);
      }
    }

    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error('Response body is null');
    }

    const decoder = new TextDecoder();
    let buffer = '';
    let chunkCount = 0;

    while (true) {
      const { done, value } = await reader.read();

      if (done) {
        onComplete?.();
        break;
      }

      // 解码新的数据块
      buffer += decoder.decode(value, { stream: true });

      // 处理 SSE 格式数据
      const lines = buffer.split('\n');
      buffer = lines.pop() || ''; // 保留最后一个不完整的行

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6).trim();
          if (data) {
            try {
              const chunk = JSON.parse(data) as ChatSendResponse;
              chunkCount++;
              // 立即调用 onChunk，不等待更多数据
              onChunk(chunk);
            } catch (e) {
              console.error('[API] Failed to parse SSE chunk:', data, e);
            }
          }
        }
      }
    }
  } catch (error) {
    console.error('[API] Request error:', error);
    onError?.(error as Error);
  }
}

/**
 * 获取会话列表
 */
export function getChatSessions(params?: { page?: number; page_size?: number }): Promise<{ items: ChatSession[]; total: number; page: number; page_size: number; total_pages: number }> {
  return api.get<{ items: ChatSession[]; total: number; page: number; page_size: number; total_pages: number }>(
    '/api/v1/chat/sessions',
    { params }
  ) as any;
}

/**
 * 获取单个会话详情
 */
export function getChatSession(sessionId: string) {
  return api.get<ChatSession>(`/api/v1/chat/sessions/${sessionId}`);
}

/**
 * 创建新会话
 */
export function createChatSession(data?: { title?: string; model?: string }) {
  return api.post<ChatSession>('/api/v1/chat/sessions', data);
}

/**
 * 更新会话
 */
export function updateChatSession(sessionId: string, data: { title?: string; model?: string }) {
  return api.put<ChatSession>(`/api/v1/chat/sessions/${sessionId}`, data);
}

/**
 * 删除会话
 */
export function deleteChatSession(sessionId: string) {
  return api.delete(`/api/v1/chat/sessions/${sessionId}`);
}

// =============================================================================
// 文章 API
// =============================================================================

export const articleAPI = {
  generate: (data: { topic: string; type: string; requirements?: string }) =>
    api.post('/api/articles/generate', data),

  rewrite: (data: { url: string; operation: string }) =>
    api.post('/api/articles/rewrite', data),

  getHistory: () =>
    api.get('/api/articles/history'),
};

// =============================================================================
// 热点 API
// =============================================================================

export const hotspotAPI = {
  getAll: (source?: string) =>
    api.get('/api/hotspots', { params: { source } }),
};

// =============================================================================
// 知识库 API
// =============================================================================

export const knowledgeAPI = {
  upload: (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/api/knowledge/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },

  list: () =>
    api.get('/api/knowledge/list'),

  delete: (id: string) =>
    api.delete(`/api/knowledge/${id}`),
};

// =============================================================================
// 推文选题 API
// =============================================================================

import type {
  UserTopic,
  TweetTopicsRecord,
  IntelligentGenerateRequest,
  ManualGenerateRequest,
  GenerateResponse
} from '@/types/tweet-topics';

export const tweetTopicsApi = {
  // 智能模式生成（使用长超时）
  async generateIntelligent(params: IntelligentGenerateRequest): Promise<GenerateResponse> {
    const data = await longTimeoutApi.post<GenerateResponse>('/api/v1/tweet-topics/generate-intelligent', params);
    return normalizeTweetTopicsResponse(data) as GenerateResponse;
  },

  // 手动模式生成（使用长超时）
  async generateManual(params: ManualGenerateRequest): Promise<GenerateResponse> {
    const data = await longTimeoutApi.post<GenerateResponse>('/api/v1/tweet-topics/generate', params);
    return normalizeTweetTopicsResponse(data) as GenerateResponse;
  },

  // 获取历史记录
  async getHistory(): Promise<TweetTopicsRecord[]> {
    const data = await api.get<TweetTopicsRecord[]>('/api/v1/tweet-topics/history');
    return data as unknown as TweetTopicsRecord[];
  },

  // 删除历史记录
  async deleteRecord(recordId: number): Promise<{ success: boolean }> {
    const data = await api.delete<{ success: boolean }>(`/api/v1/tweet-topics/${recordId}`);
    return data as unknown as { success: boolean };
  },

  // 获取用户主题
  async getUserTopics(): Promise<{ topics: UserTopic[] }> {
    const data = await api.get<{ topics: UserTopic[] }>('/api/v1/tweet-topics/user-topics');
    return data as unknown as { topics: UserTopic[] };
  },

  // 创建主题
  async createUserTopic(data: {
    topic_name: string;
    description?: string;
  }): Promise<{ topic: UserTopic }> {
    const result = await api.post<{ topic: UserTopic }>('/api/v1/tweet-topics/user-topics', data);
    return result as unknown as { topic: UserTopic };
  },

  // 删除主题
  async deleteUserTopic(topicId: number): Promise<{ success: boolean }> {
    const data = await api.delete<{ success: boolean }>(`/api/v1/tweet-topics/user-topics/${topicId}`);
    return data as unknown as { success: boolean };
  }
};

export function extractApiError(error: unknown, fallback: string): string {
  if (typeof error === 'object' && error !== null) {
    const apiError = error as {
      response?: { data?: { detail?: string; message?: string } };
      message?: string;
    };
    return apiError.response?.data?.detail || apiError.response?.data?.message || apiError.message || fallback;
  }

  return fallback;
}

// =============================================================================
// 用户/头像 API
// =============================================================================

export const userApi = {
  // 上传头像文件
  async uploadAvatar(file: File): Promise<{ avatar_url: string; avatar_source: string }> {
    const formData = new FormData();
    formData.append('file', file);
    const data = await api.post<{ avatar_url: string; avatar_source: string }>(
      '/api/v1/auth/upload-avatar',
      formData,
      {
        headers: { 'Content-Type': 'multipart/form-data' },
      }
    );
    return data as unknown as { avatar_url: string; avatar_source: string };
  },

  // 通过 URL 更新头像
  async updateAvatar(avatarUrl: string): Promise<{ avatar_url: string; avatar_source: string }> {
    const data = await api.put<{ avatar_url: string; avatar_source: string }>('/api/v1/auth/update-avatar', {
      avatar_url: avatarUrl,
    });
    return data as unknown as { avatar_url: string; avatar_source: string };
  },

  // 更新用户资料
  async updateProfile(data: {
    display_name?: string;
    bio?: string;
  }): Promise<{ message: string }> {
    const result = await api.put<{ message: string }>('/api/v1/auth/update-profile', data);
    return result as unknown as { message: string };
  },

  // 获取当前用户信息
  async getCurrentUser(): Promise<{
    id: number;
    username: string;
    email: string;
    display_name?: string;
    avatar?: string;
    bio?: string;
    membership_tier?: string;
    is_admin?: boolean;
  }> {
    const data = await api.get('/api/v1/auth/me');
    return data as unknown as {
      id: number;
      username: string;
      email: string;
      display_name?: string;
      avatar?: string;
      bio?: string;
      membership_tier?: string;
      is_admin?: boolean;
    };
  }
};

// =============================================================================
// Membership Tier API
// =============================================================================

import type {
  MembershipTier,
  TierDefaults,
  AllTierDefaults,
  TierModelConfig,
  GlobalLLMProvider,
  UserSearchResult,
  AvailableModelsResponse,
  UserQuotaResponse
} from '@/types/api';

/**
 * 获取用户等级的可用模型列表（自动继承低等级模型）
 */
export async function getAvailableModels(): Promise<AvailableModelsResponse> {
  return api.get('/api/v1/settings/available-models');
}

/**
 * 获取所有等级的默认配置（管理员）
 */
export async function getAllTierDefaults(): Promise<AllTierDefaults> {
  return api.get('/api/v1/admin/tier-defaults');
}

/**
 * 获取指定等级的默认配置（管理员）
 */
export async function getTierDefaults(tier: MembershipTier): Promise<TierDefaults> {
  return api.get(`/api/v1/admin/tier-defaults/${tier}`);
}

/**
 * 更新等级默认配置（管理员）
 */
export async function updateTierDefaults(
  tier: MembershipTier,
  data: {
    default_chat_model?: string;
    default_writer_model?: string;
    article_limit_per_month?: number;
  }
): Promise<{ message: string; tier: string }> {
  return api.put(`/api/v1/admin/tier-defaults/${tier}`, { tier, ...data });
}

/**
 * 获取全局 LLM 提供商列表（管理员）
 */
export async function getGlobalProviders(): Promise<{ providers: GlobalLLMProvider[] }> {
  return api.get('/api/v1/admin/global-providers');
}

/**
 * 更新全局提供商（管理员）
 * models 结构: [{"name": "deepseek-chat", "min_tier": "free"}]
 */
export async function updateGlobalProvider(
  data: {
    provider_id: string;
    base_url: string;
    models: TierModelConfig[];
    api_key?: string;
    enabled: boolean;
  }
): Promise<{ message: string; provider_id: string }> {
  return api.put('/api/v1/admin/global-providers', data);
}

/**
 * 删除全局提供商（管理员）
 */
export async function deleteGlobalProvider(providerId: string): Promise<{ message: string; provider_id: string }> {
  return api.delete(`/api/v1/admin/global-providers/${providerId}`);
}

/**
 * 搜索用户（管理员）
 */
export async function searchUsers(
  query: string,
  limit: number = 20,
  offset: number = 0
): Promise<{ users: UserSearchResult[]; total: number; limit: number; offset: number }> {
  return api.get('/api/v1/admin/users/search', {
    params: { q: query, limit, offset }
  });
}

/**
 * 更新用户等级（管理员）
 */
export async function updateUserTier(
  userId: number,
  tier: MembershipTier
): Promise<{ message: string; user_id: number; username: string; membership_tier: string }> {
  return api.put(`/api/v1/admin/users/${userId}/membership`, { tier });
}

/**
 * 检查用户文章配额
 */
export async function checkUserQuota(): Promise<UserQuotaResponse> {
  const quota = await api.get<{
    plan_quota: number;
    plan_used: number;
    plan_remaining: number;
    total_remaining: number;
  }>('/api/v1/subscription/quota') as unknown as {
    plan_quota: number;
    plan_used: number;
    plan_remaining: number;
    total_remaining: number;
  };

  return {
    allowed: quota.total_remaining > 0,
    used: quota.plan_used,
    limit: quota.plan_quota,
    remaining: quota.plan_remaining,
  };
}
