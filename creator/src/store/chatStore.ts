import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export interface Message {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: number
  isStreaming?: boolean
}

export interface Session {
  id: string
  title: string
  model: string
  messages: Message[]
  createdAt: number
  updatedAt: number
}

interface ChatStore {
  // 当前会话
  currentSession: Session | null
  sessions: Session[]
  isLoading: boolean
  error: string | null

  // 操作
  setCurrentSession: (session: Session | null) => void
  createSession: (title?: string, model?: string) => Promise<void>
  updateSession: (sessionId: string, data: Partial<Session>) => Promise<void>
  deleteSession: (sessionId: string) => Promise<void>
  loadSessions: () => Promise<void>

  // 消息操作
  addMessage: (message: Omit<Message, 'id' | 'timestamp'>) => void
  updateMessage: (messageId: string, content: string) => void
  appendToLastMessage: (content: string) => void
  sendMessage: (content: string, sessionId?: string) => Promise<void>
  clearMessages: () => void

  // UI 状态
  setIsLoading: (loading: boolean) => void
  setError: (error: string | null) => void
}

export const useChatStore = create<ChatStore>()(
  persist(
    (set, get) => ({
      currentSession: null,
      sessions: [],
      isLoading: false,
      error: null,

      setCurrentSession: (session) => set({ currentSession: session }),

      createSession: async (title = '新对话', model = 'gpt-4o-mini') => {
        try {
          set({ isLoading: true, error: null })

          const response = await fetch('/api/v1/chat/sessions', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${localStorage.getItem('supawriter-auth')?.match(/"token":"(.*?)"/)?.[1] || ''}`,
            },
            body: JSON.stringify({ title, model }),
          })

          if (!response.ok) throw new Error('创建会话失败')

          const newSession = await response.json()

          set((state) => ({
            sessions: [newSession, ...state.sessions],
            currentSession: newSession,
            isLoading: false,
          }))
        } catch (error) {
          set({ error: (error as Error).message, isLoading: false })
          throw error
        }
      },

      updateSession: async (sessionId, data) => {
        try {
          await fetch(`/api/v1/chat/sessions/${sessionId}`, {
            method: 'PUT',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${localStorage.getItem('supawriter-auth')?.match(/"token":"(.*?)"/)?.[1] || ''}`,
            },
            body: JSON.stringify(data),
          })

          set((state) => ({
            sessions: state.sessions.map((s) =>
              s.id === sessionId ? { ...s, ...data, updatedAt: Date.now() } : s
            ),
            currentSession:
              state.currentSession?.id === sessionId
                ? { ...state.currentSession, ...data, updatedAt: Date.now() }
                : state.currentSession,
          }))
        } catch (error) {
          set({ error: (error as Error).message })
        }
      },

      deleteSession: async (sessionId) => {
        try {
          await fetch(`/api/v1/chat/sessions/${sessionId}`, {
            method: 'DELETE',
            headers: {
              'Authorization': `Bearer ${localStorage.getItem('supawriter-auth')?.match(/"token":"(.*?)"/)?.[1] || ''}`,
            },
          })

          set((state) => ({
            sessions: state.sessions.filter((s) => s.id !== sessionId),
            currentSession:
              state.currentSession?.id === sessionId ? null : state.currentSession,
          }))
        } catch (error) {
          set({ error: (error as Error).message })
        }
      },

      loadSessions: async () => {
        try {
          set({ isLoading: true, error: null })

          const response = await fetch('/api/v1/chat/sessions', {
            headers: {
              'Authorization': `Bearer ${localStorage.getItem('supawriter-auth')?.match(/"token":"(.*?)"/)?.[1] || ''}`,
            },
          })

          if (!response.ok) throw new Error('加载会话失败')

          const sessions = await response.json()

          set({ sessions, isLoading: false })
        } catch (error) {
          set({ error: (error as Error).message, isLoading: false })
        }
      },

      addMessage: (message) => {
        const newMessage: Message = {
          ...message,
          id: `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
          timestamp: Date.now(),
        }

        set((state) => {
          const sessions = state.sessions.map((s) => {
            if (s.id === state.currentSession?.id) {
              return {
                ...s,
                messages: [...s.messages, newMessage],
                updatedAt: Date.now(),
              }
            }
            return s
          })

          return {
            sessions,
            currentSession: state.currentSession
              ? {
                  ...state.currentSession,
                  messages: [...state.currentSession.messages, newMessage],
                  updatedAt: Date.now(),
                }
              : null,
          }
        })
      },

      updateMessage: (messageId, content) => {
        set((state) => {
          const sessions = state.sessions.map((s) => ({
            ...s,
            messages: s.messages.map((m) =>
              m.id === messageId ? { ...m, content, isStreaming: false } : m
            ),
          }))

          return {
            sessions,
            currentSession: state.currentSession
              ? {
                  ...state.currentSession,
                  messages: state.currentSession.messages.map((m) =>
                    m.id === messageId ? { ...m, content, isStreaming: false } : m
                  ),
                }
              : null,
          }
        })
      },

      appendToLastMessage: (content) => {
        set((state) => {
          const sessions = state.sessions.map((s) => {
            if (s.id === state.currentSession?.id && s.messages.length > 0) {
              const lastMessage = s.messages[s.messages.length - 1]
              return {
                ...s,
                messages: [
                  ...s.messages.slice(0, -1),
                  { ...lastMessage, content: lastMessage.content + content },
                ],
              }
            }
            return s
          })

          return {
            sessions,
            currentSession: state.currentSession &&
              state.currentSession.messages.length > 0
              ? {
                  ...state.currentSession,
                  messages: [
                    ...state.currentSession.messages.slice(0, -1),
                    {
                      ...state.currentSession.messages[
                        state.currentSession.messages.length - 1
                      ],
                      content:
                        state.currentSession.messages[
                          state.currentSession.messages.length - 1
                        ].content + content,
                    },
                  ],
                }
              : state.currentSession,
          }
        })
      },

      sendMessage: async (content, sessionId) => {
        try {
          set({ isLoading: true, error: null })

          const currentSessionId = sessionId || get().currentSession?.id

          // 添加用户消息
          get().addMessage({ role: 'user', content })

          // 添加空的助手消息用于流式更新
          get().addMessage({ role: 'assistant', content: '', isStreaming: true })

          const response = await fetch('/api/v1/chat/send', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${localStorage.getItem('supawriter-auth')?.match(/"token":"(.*?)"/)?.[1] || ''}`,
            },
            body: JSON.stringify({
              message: content,
              session_id: currentSessionId,
            }),
          })

          if (!response.ok) throw new Error('发送消息失败')

          // 处理 SSE 流式响应
          const reader = response.body?.getReader()
          const decoder = new TextDecoder()

          if (reader) {
            let buffer = ''

            while (true) {
              const { done, value } = await reader.read()

              if (done) break

              buffer += decoder.decode(value, { stream: true })
              const lines = buffer.split('\n')
              buffer = lines.pop() || ''

              for (const line of lines) {
                if (line.startsWith('data: ')) {
                  try {
                    const data = JSON.parse(line.slice(6))

                    if (data.type === 'assistant_chunk') {
                      get().appendToLastMessage(data.text)
                    } else if (data.type === 'assistant_end') {
                      get().updateMessage(
                        get().currentSession?.messages[
                          get().currentSession.messages.length - 1
                        ].id || '',
                        data.content || ''
                      )
                      set({ isLoading: false })
                    } else if (data.type === 'error') {
                      set({ error: data.error, isLoading: false })
                    }
                  } catch (e) {
                    console.error('Error parsing SSE data:', e)
                  }
                }
              }
            }
          }
        } catch (error) {
          set({ error: (error as Error).message, isLoading: false })
          throw error
        }
      },

      clearMessages: () => {
        set((state) => ({
          sessions: state.sessions.map((s) =>
            s.id === state.currentSession?.id ? { ...s, messages: [] } : s
          ),
          currentSession: state.currentSession
            ? { ...state.currentSession, messages: [] }
            : null,
        }))
      },

      setIsLoading: (loading) => set({ isLoading: loading }),
      setError: (error) => set({ error }),
    }),
    {
      name: 'supawriter-chat',
      partialize: (state) => ({
        sessions: state.sessions,
        currentSession: state.currentSession
          ? {
              ...state.currentSession,
              messages: state.currentSession.messages.slice(-50), // 只保存最后50条消息
            }
          : null,
      }),
    }
  )
)
