import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export interface Article {
  id: number
  user_id: number
  title: string
  slug: string
  content: string
  html_content: string
  cover_image: string | null
  status: 'draft' | 'published' | 'archived'
  seo_title: string | null
  seo_desc: string | null
  seo_keywords: string | null
  view_count: number
  like_count: number
  comment_count: number
  favorite_count: number
  tags: string[]
  created_at: string
  updated_at: string
  published_at: string | null
  metadata: Record<string, any>
}

export interface SearchResultItem {
  title: string
  url: string
  snippet?: string
  source?: string
}

export interface ReferenceItem {
  title: string
  url: string
}

export interface ArticleTask {
  id: string
  user_id: number
  topic: string
  article_type: string
  custom_style: string | null
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
  progress: number
  progress_text: string
  live_article: string | null
  error_message: string | null
  created_at: string
  updated_at: string
  completed_at: string | null
  article_id: number | null
  search_results?: SearchResultItem[]
  search_stats?: Record<string, any>
  outline?: Record<string, any>
  references?: ReferenceItem[]
  article_metadata?: Record<string, any>
}

interface ArticleStore {
  // 文章数据
  articles: Article[]
  currentArticle: Article | null
  isLoading: boolean
  error: string | null

  // 文章操作
  loadArticles: (params?: { status?: string; page?: number; page_size?: number }) => Promise<void>
  loadArticle: (id: number) => Promise<void>
  createArticle: (data: { title: string; content?: string; tags?: string[] }) => Promise<void>
  updateArticle: (id: number, data: Partial<Article>) => Promise<void>
  deleteArticle: (id: number) => Promise<void>
  publishArticle: (id: number, data: { seo_title?: string; seo_desc?: string; tags?: string[] }) => Promise<void>
  unpublishArticle: (id: number) => Promise<void>

  // 生成任务
  generateArticle: (data: { topic: string; article_type?: string; custom_style?: string }) => Promise<string>

  // UI 状态
  setCurrentArticle: (article: Article | null) => void
  setError: (error: string | null) => void
  clearError: () => void
}

const getToken = () => {
  const authData = localStorage.getItem('supawriter-auth')
  if (authData) {
    const match = authData.match(/"token":"(.*?)"/)
    return match ? match[1] : ''
  }
  return ''
}

export const useArticleStore = create<ArticleStore>()(
  persist(
    (set, get) => ({
      articles: [],
      currentArticle: null,
      isLoading: false,
      error: null,

      setCurrentArticle: (article) => set({ currentArticle: article }),

      loadArticles: async (params = {}) => {
        try {
          set({ isLoading: true, error: null })

          const queryParams = new URLSearchParams()
          if (params.status) queryParams.append('status', params.status)
          if (params.page) queryParams.append('page', params.page.toString())
          if (params.page_size) queryParams.append('page_size', params.page_size.toString())

          const response = await fetch(`/api/v1/articles?${queryParams}`, {
            headers: {
              'Authorization': `Bearer ${getToken()}`,
            },
          })

          if (!response.ok) throw new Error('加载文章失败')

          const data = await response.json()
          const articles = data.items || data

          set({ articles, isLoading: false })
        } catch (error) {
          set({ error: (error as Error).message, isLoading: false })
        }
      },

      loadArticle: async (id) => {
        try {
          set({ isLoading: true, error: null })

          const response = await fetch(`/api/v1/articles/${id}`, {
            headers: {
              'Authorization': `Bearer ${getToken()}`,
            },
          })

          if (!response.ok) throw new Error('加载文章失败')

          const article = await response.json()

          set({ currentArticle: article, isLoading: false })
        } catch (error) {
          set({ error: (error as Error).message, isLoading: false })
        }
      },

      createArticle: async (data) => {
        try {
          set({ isLoading: true, error: null })

          const response = await fetch('/api/v1/articles', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${getToken()}`,
            },
            body: JSON.stringify(data),
          })

          if (!response.ok) throw new Error('创建文章失败')

          const article = await response.json()

          set((state) => ({
            articles: [article, ...state.articles],
            currentArticle: article,
            isLoading: false,
          }))

          return article
        } catch (error) {
          set({ error: (error as Error).message, isLoading: false })
          throw error
        }
      },

      updateArticle: async (id, data) => {
        try {
          set({ isLoading: true, error: null })

          const response = await fetch(`/api/v1/articles/${id}`, {
            method: 'PUT',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${getToken()}`,
            },
            body: JSON.stringify(data),
          })

          if (!response.ok) throw new Error('更新文章失败')

          const article = await response.json()

          set((state) => ({
            articles: state.articles.map((a) => (a.id === id ? article : a)),
            currentArticle: state.currentArticle?.id === id ? article : state.currentArticle,
            isLoading: false,
          }))
        } catch (error) {
          set({ error: (error as Error).message, isLoading: false })
          throw error
        }
      },

      deleteArticle: async (id) => {
        try {
          set({ isLoading: true, error: null })

          const response = await fetch(`/api/v1/articles/${id}`, {
            method: 'DELETE',
            headers: {
              'Authorization': `Bearer ${getToken()}`,
            },
          })

          if (!response.ok) throw new Error('删除文章失败')

          set((state) => ({
            articles: state.articles.filter((a) => a.id !== id),
            currentArticle: state.currentArticle?.id === id ? null : state.currentArticle,
            isLoading: false,
          }))
        } catch (error) {
          set({ error: (error as Error).message, isLoading: false })
          throw error
        }
      },

      publishArticle: async (id, data) => {
        try {
          set({ isLoading: true, error: null })

          const response = await fetch(`/api/v1/articles/${id}/publish`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${getToken()}`,
            },
            body: JSON.stringify(data),
          })

          if (!response.ok) throw new Error('发布文章失败')

          const article = await response.json()

          set((state) => ({
            articles: state.articles.map((a) => (a.id === id ? article : a)),
            currentArticle: state.currentArticle?.id === id ? article : state.currentArticle,
            isLoading: false,
          }))
        } catch (error) {
          set({ error: (error as Error).message, isLoading: false })
          throw error
        }
      },

      unpublishArticle: async (id) => {
        try {
          set({ isLoading: true, error: null })

          const response = await fetch(`/api/v1/articles/${id}/unpublish`, {
            method: 'POST',
            headers: {
              'Authorization': `Bearer ${getToken()}`,
            },
          })

          if (!response.ok) throw new Error('取消发布失败')

          const article = await response.json()

          set((state) => ({
            articles: state.articles.map((a) => (a.id === id ? article : a)),
            currentArticle: state.currentArticle?.id === id ? article : state.currentArticle,
            isLoading: false,
          }))
        } catch (error) {
          set({ error: (error as Error).message, isLoading: false })
          throw error
        }
      },

      generateArticle: async (data) => {
        try {
          set({ isLoading: true, error: null })

          const response = await fetch('/api/v1/articles/generate', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${getToken()}`,
            },
            body: JSON.stringify(data),
          })

          if (!response.ok) throw new Error('创建生成任务失败')

          const result = await response.json()

          set({ isLoading: false })

          return result.task_id
        } catch (error) {
          set({ error: (error as Error).message, isLoading: false })
          throw error
        }
      },

      setError: (error) => set({ error }),
      clearError: () => set({ error: null }),
    }),
    {
      name: 'supawriter-articles',
      partialize: (state) => ({
        articles: state.articles.slice(0, 50), // 只缓存前50篇
      }),
    }
  )
)
