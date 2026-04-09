import { create } from 'zustand'
import { ArticleTask } from './articleStore'
import { connectWebSocket } from '@lib/websocket'

interface QueueStore {
  tasks: ArticleTask[]
  activeTask: ArticleTask | null
  isLoading: boolean
  error: string | null

  // 操作
  loadQueue: () => Promise<void>
  loadTaskProgress: (taskId: string) => Promise<void>
  addTask: (task: ArticleTask) => void
  updateTask: (taskId: string, data: Partial<ArticleTask>) => void
  removeTask: (taskId: string) => void
  setActiveTask: (task: ArticleTask | null) => void
  cancelTask: (taskId: string) => Promise<void>

  // WebSocket
  connectWebSocket: (userId: string) => void
  disconnectWebSocket: () => void

  // UI 状态
  setError: (error: string | null) => void
}

const getToken = () => {
  const authData = localStorage.getItem('supawriter-auth')
  if (authData) {
    const match = authData.match(/"token":"(.*?)"/)
    return match ? match[1] : ''
  }
  return ''
}

export const useQueueStore = create<QueueStore>()((set, get) => ({
  tasks: [],
  activeTask: null,
  isLoading: false,
  error: null,

  loadQueue: async () => {
    try {
      set({ isLoading: true, error: null })

      const response = await fetch('/api/v1/articles/queue', {
        headers: {
          'Authorization': `Bearer ${getToken()}`,
        },
      })

      if (!response.ok) throw new Error('加载队列失败')

      const tasks = await response.json()

      // 更新活动任务
      const activeTask = tasks.find((t: ArticleTask) => t.status === 'running') || null

      set({ tasks, activeTask, isLoading: false })
    } catch (error) {
      set({ error: (error as Error).message, isLoading: false })
    }
  },

  loadTaskProgress: async (taskId) => {
    try {
      const response = await fetch(`/api/v1/articles/progress/${taskId}`, {
        headers: {
          'Authorization': `Bearer ${getToken()}`,
        },
      })

      if (!response.ok) throw new Error('加载进度失败')

      const progressData = await response.json()

      set((state) => ({
        tasks: state.tasks.map((t) =>
          t.id === taskId
            ? {
                ...t,
                progress: progressData.progress,
                progress_text: progressData.progress_text,
                live_article: progressData.live_article,
                status: progressData.status,
              }
            : t
        ),
        activeTask:
          state.activeTask?.id === taskId
            ? {
                ...state.activeTask,
                progress: progressData.progress,
                progress_text: progressData.progress_text,
                live_article: progressData.live_article,
                status: progressData.status,
              }
            : state.activeTask,
      }))
    } catch (error) {
      console.error('Failed to load task progress:', error)
    }
  },

  addTask: (task) => {
    set((state) => ({
      tasks: [task, ...state.tasks],
    }))
  },

  updateTask: (taskId, data) => {
    set((state) => ({
      tasks: state.tasks.map((t) => (t.id === taskId ? { ...t, ...data } : t)),
      activeTask:
        state.activeTask?.id === taskId
          ? { ...state.activeTask, ...data }
          : state.activeTask,
    }))
  },

  removeTask: (taskId) => {
    set((state) => ({
      tasks: state.tasks.filter((t) => t.id !== taskId),
      activeTask: state.activeTask?.id === taskId ? null : state.activeTask,
    }))
  },

  setActiveTask: (task) => set({ activeTask: task }),

  cancelTask: async (taskId) => {
    try {
      set({ isLoading: true, error: null })

      const response = await fetch(`/api/v1/articles/queue/${taskId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${getToken()}`,
        },
      })

      if (!response.ok) throw new Error('取消任务失败')

      set((state) => ({
        tasks: state.tasks.map((t) =>
          t.id === taskId ? { ...t, status: 'cancelled' as const } : t
        ),
        activeTask:
          state.activeTask?.id === taskId
            ? { ...state.activeTask, status: 'cancelled' as const }
            : state.activeTask,
        isLoading: false,
      }))
    } catch (error) {
      set({ error: (error as Error).message, isLoading: false })
      throw error
    }
  },

  connectWebSocket: (userId) => {
    const wsClient = connectWebSocket(userId)

    // 监听文章进度更新
    wsClient.on('article_progress', (data: any) => {
      const { task_id, progress, progress_text, live_article, search_results, search_stats, outline, references, article_metadata } = data
      const update: Partial<ArticleTask> = { progress, progress_text, live_article }
      if (search_results) update.search_results = search_results
      if (search_stats) update.search_stats = search_stats
      if (outline) update.outline = outline
      if (references) update.references = references
      if (article_metadata) update.article_metadata = article_metadata
      get().updateTask(task_id, update)
    })

    // 监听任务完成
    wsClient.on('article_completed', (data: any) => {
      const { task_id, article_id, references, article_metadata } = data
      const update: Partial<ArticleTask> = {
        status: 'completed',
        article_id,
        progress: 100,
      }
      if (references) update.references = references
      if (article_metadata) update.article_metadata = article_metadata
      get().updateTask(task_id, update)
    })

    // 监听任务失败
    wsClient.on('article_failed', (data: any) => {
      const { task_id, error_message } = data
      get().updateTask(task_id, {
        status: 'failed',
        error_message,
      })
    })
  },

  disconnectWebSocket: () => {
    // WebSocket 客户端会自动处理断开连接
  },

  setError: (error) => set({ error }),
}))
