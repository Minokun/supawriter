import axios, { AxiosError, InternalAxiosError } from 'axios'
import { useAuthStore } from '@store/authStore'

// 创建 axios 实例
export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api/v1',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 请求拦截器 - 添加 token
api.interceptors.request.use(
  (config) => {
    const token = useAuthStore.getState().token
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器 - 处理错误
api.interceptors.response.use(
  (response) => response.data,
  (error: AxiosError) => {
    // 处理 401 未授权错误
    if (error.response?.status === 401) {
      // 清除认证信息
      useAuthStore.getState().logout()
      // 重定向到登录页
      window.location.href = '/auth/login'
    }

    // 返回错误信息
    const message = error.response?.data?.detail || error.message || '请求失败'
    return Promise.reject(new Error(message))
  }
)

// 文章相关 API
export const articleAPI = {
  create: (data: { title: string; content?: string; tags?: string[] }) =>
    api.post('/articles', data),

  list: (params?: { status?: string; page?: number; page_size?: number }) =>
    api.get('/articles', { params }),

  get: (id: number) =>
    api.get(`/articles/${id}`),

  update: (id: number, data: { title?: string; content?: string; tags?: string[] }) =>
    api.put(`/articles/${id}`, data),

  delete: (id: number) =>
    api.delete(`/articles/${id}`),

  publish: (id: number, data: { seo_title?: string; seo_desc?: string; tags?: string[] }) =>
    api.post(`/articles/${id}/publish`, data),

  unpublish: (id: number) =>
    api.post(`/articles/${id}/unpublish`),

  generate: (data: { topic: string; article_type?: string; custom_style?: string }) =>
    api.post('/articles/generate', data),

  getQueue: () =>
    api.get('/articles/queue'),

  getProgress: (taskId: string) =>
    api.get(`/articles/progress/${taskId}`),
}

// AI 助手 API
export const chatAPI = {
  send: (data: { message: string; session_id?: string; model?: string }) => {
    // SSE 流式响应
    return fetch('/api/v1/chat/send', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${useAuthStore.getState().token}`,
      },
      body: JSON.stringify(data),
    })
  },

  listSessions: (params?: { page?: number; page_size?: number }) =>
    api.get('/chat/sessions', { params }),

  getSession: (sessionId: string) =>
    api.get(`/chat/sessions/${sessionId}`),

  createSession: (data?: { title?: string; model?: string }) =>
    api.post('/chat/sessions', data || {}),

  updateSession: (sessionId: string, data: { title?: string; model?: string }) =>
    api.put(`/chat/sessions/${sessionId}`, data),

  deleteSession: (sessionId: string) =>
    api.delete(`/chat/sessions/${sessionId}`),
}

// 热点 API
export const hotspotAPI = {
  getAll: (params?: { source?: string; limit?: number }) =>
    api.get('/hotspots', { params }),

  getSources: () =>
    api.get('/hotspots/sources'),
}

// 新闻 API
export const newsAPI = {
  getAll: (params?: { source?: string; category?: string; limit?: number }) =>
    api.get('/news', { params }),

  getSources: () =>
    api.get('/news/sources'),
}

// 推文选题 API
export const tweetTopicsAPI = {
  generate: (data: { news_source: string; news_count: number; topic_count: number }) =>
    api.post('/tweet-topics/generate', data),

  history: () =>
    api.get('/tweet-topics/history'),

  delete: (id: number) =>
    api.delete(`/tweet-topics/${id}`),
}

export default api
