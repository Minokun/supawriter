import { useEffect } from 'react'
import { useChatStore } from '@store/chatStore'
import { MessageSquare, Plus, Settings, Trash2 } from 'lucide-react'
import SessionList from './SessionList'
import ChatBox from './ChatBox'
import { useNavigate } from 'react-router-dom'

function AIChat() {
  const navigate = useNavigate()
  const {
    currentSession,
    sessions,
    isLoading,
    error,
    loadSessions,
    createSession,
    deleteSession,
    setCurrentSession,
    setError,
  } = useChatStore()

  useEffect(() => {
    loadSessions().catch((err) => {
      console.error('Failed to load sessions:', err)
    })

    // 如果没有当前会话且有会话列表，加载第一个会话
    if (!currentSession && sessions.length > 0) {
      setCurrentSession(sessions[0])
    }
  }, [])

  const handleNewChat = async () => {
    try {
      await createSession()
    } catch (err) {
      console.error('Failed to create session:', err)
    }
  }

  const handleDeleteSession = async (sessionId: string) => {
    try {
      await deleteSession(sessionId)
      if (currentSession?.id === sessionId) {
        setCurrentSession(sessions.find((s) => s.id !== sessionId) || null)
      }
    } catch (err) {
      console.error('Failed to delete session:', err)
    }
  }

  const handleSelectSession = (sessionId: string) => {
    const session = sessions.find((s) => s.id === sessionId)
    if (session) {
      setCurrentSession(session)
    }
  }

  return (
    <div className="h-[calc(100vh-8rem)] flex gap-6">
      {/* 侧边栏 - 会话列表 */}
      <div className="w-80 bg-card rounded-xl shadow-md flex flex-col overflow-hidden">
        {/* 头部 */}
        <div className="p-4 border-b border-border">
          <button
            onClick={handleNewChat}
            disabled={isLoading}
            className="w-full flex items-center justify-center gap-2 bg-primary text-white px-4 py-3 rounded-lg font-medium hover:bg-primary-dark transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Plus size={20} />
            <span>新建对话</span>
          </button>
        </div>

        {/* 会话列表 */}
        <div className="flex-1 overflow-y-auto">
          <SessionList
            sessions={sessions}
            currentSessionId={currentSession?.id}
            onSelectSession={handleSelectSession}
            onDeleteSession={handleDeleteSession}
          />
        </div>

        {/* 底部设置 */}
        <div className="p-4 border-t border-border">
          <button
            onClick={() => navigate('/settings')}
            className="w-full flex items-center justify-center gap-2 text-text-secondary hover:text-primary transition-colors px-4 py-2 rounded-lg hover:bg-background"
          >
            <Settings size={18} />
            <span className="text-sm">设置</span>
          </button>
        </div>
      </div>

      {/* 聊天区域 */}
      <div className="flex-1 bg-card rounded-xl shadow-md flex flex-col overflow-hidden">
        {/* 头部 */}
        <div className="p-4 border-b border-border flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-primary/10 rounded-lg">
              <MessageSquare className="text-primary" size={24} />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-text-primary">
                {currentSession?.title || 'AI 助手'}
              </h2>
              <p className="text-sm text-text-muted">
                {currentSession?.model || 'gpt-4o-mini'}
              </p>
            </div>
          </div>

          {currentSession && (
            <button
              onClick={() => handleDeleteSession(currentSession.id)}
              className="p-2 text-text-muted hover:text-red-500 transition-colors rounded-lg hover:bg-red-50"
              title="删除对话"
            >
              <Trash2 size={18} />
            </button>
          )}
        </div>

        {/* 错误提示 */}
        {error && (
          <div className="mx-4 mt-4 p-3 bg-red-50 border border-red-200 text-red-600 rounded-lg text-sm">
            {error}
            <button
              onClick={() => setError(null)}
              className="ml-2 text-red-800 hover:text-red-900"
            >
              ✕
            </button>
          </div>
        )}

        {/* 聊天框 */}
        <ChatBox />
      </div>
    </div>
  )
}

export default AIChat
