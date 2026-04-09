import { Session } from '@store/chatStore'
import { MessageSquare, Trash2 } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import { zhCN } from 'date-fns/locale'

interface SessionListProps {
  sessions: Session[]
  currentSessionId: string | null
  onSelectSession: (sessionId: string) => void
  onDeleteSession: (sessionId: string) => void
}

function SessionList({
  sessions,
  currentSessionId,
  onSelectSession,
  onDeleteSession,
}: SessionListProps) {
  const handleDelete = (e: React.MouseEvent, sessionId: string) => {
    e.stopPropagation()
    if (confirm('确定要删除这个对话吗？')) {
      onDeleteSession(sessionId)
    }
  }

  if (sessions.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-text-muted px-8 text-center">
        <MessageSquare size={48} className="mb-4 opacity-50" />
        <p className="text-sm">还没有对话记录</p>
        <p className="text-xs mt-2">点击"新建对话"开始聊天</p>
      </div>
    )
  }

  return (
    <div className="p-2 space-y-1">
      {sessions.map((session) => (
        <div
          key={session.id}
          onClick={() => onSelectSession(session.id)}
          className={`group flex items-center gap-3 p-3 rounded-lg cursor-pointer transition-colors relative ${
            currentSessionId === session.id
              ? 'bg-primary/10 border border-primary/20'
              : 'hover:bg-background'
          }`}
        >
          {/* 图标 */}
          <div
            className={`p-2 rounded-lg ${
              currentSessionId === session.id
                ? 'bg-primary/20'
                : 'bg-background'
            }`}
          >
            <MessageSquare
              size={18}
              className={
                currentSessionId === session.id ? 'text-primary' : 'text-text-muted'
              }
            />
          </div>

          {/* 内容 */}
          <div className="flex-1 min-w-0">
            <h3
              className={`text-sm font-medium truncate ${
                currentSessionId === session.id
                  ? 'text-primary'
                  : 'text-text-primary'
              }`}
            >
              {session.title}
            </h3>
            <p className="text-xs text-text-muted mt-0.5">
              {formatDistanceToNow(new Date(session.updatedAt), {
                addSuffix: true,
                locale: zhCN,
              })}
            </p>
          </div>

          {/* 删除按钮 */}
          <button
            onClick={(e) => handleDelete(e, session.id)}
            className="opacity-0 group-hover:opacity-100 p-1.5 text-text-muted hover:text-red-500 hover:bg-red-50 rounded-lg transition-all"
            title="删除对话"
          >
            <Trash2 size={14} />
          </button>
        </div>
      ))}
    </div>
  )
}

export default SessionList
