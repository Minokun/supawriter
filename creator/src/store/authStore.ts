import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface User {
  id: number
  username: string
  email: string
  display_name?: string
  avatar?: string
  bio?: string
}

interface AuthStore {
  // 状态
  token: string | null
  user: User | null
  isLoading: boolean
  error: string | null

  // 操作
  setToken: (token: string) => void
  setUser: (user: User | null) => void
  login: (email: string, password: string) => Promise<void>
  register: (username: string, email: string, password: string) => Promise<void>
  logout: () => Promise<void>
  clearError: () => void
}

export const useAuthStore = create<AuthStore>()(
  persist(
    (set) => ({
      // 初始状态
      token: null,
      user: null,
      isLoading: false,
      error: null,

      // 设置 token
      setToken: (token) => set({ token }),

      // 设置用户信息
      setUser: (user) => set({ user }),

      // 登录
      login: async (email, password) => {
        set({ isLoading: true, error: null })

        try {
          const response = await fetch('/api/v1/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password }),
          })

          const data = await response.json()

          if (!response.ok) {
            throw new Error(data.detail || '登录失败')
          }

          set({
            token: data.access_token,
            user: data.user,
            isLoading: false,
          })
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : '登录失败',
            isLoading: false,
          })
          throw error
        }
      },

      // 注册
      register: async (username, email, password) => {
        set({ isLoading: true, error: null })

        try {
          const response = await fetch('/api/v1/auth/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, email, password }),
          })

          const data = await response.json()

          if (!response.ok) {
            throw new Error(data.detail || '注册失败')
          }

          set({
            token: data.access_token,
            user: data.user,
            isLoading: false,
          })
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : '注册失败',
            isLoading: false,
          })
          throw error
        }
      },

      // 登出
      logout: async () => {
        try {
          // 调用登出 API（可选）
          await fetch('/api/v1/auth/logout', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${useAuthStore.getState().token}`,
            },
          })
        } catch (error) {
          console.error('Logout error:', error)
        } finally {
          // 清除本地状态
          set({ token: null, user: null })
        }
      },

      // 清除错误
      clearError: () => set({ error: null }),
    }),
    {
      name: 'supawriter-auth',
      partialize: (state) => ({ token: state.token, user: state.user }),
    }
  )
)
