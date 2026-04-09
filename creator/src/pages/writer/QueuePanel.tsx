import { useQueueStore } from '@store/queueStore'
import { Clock, CheckCircle2, XCircle, X, Loader2, FileText } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import { zhCN } from 'date-fns/locale'
import ReactMarkdown from 'react-markdown'

function QueuePanel() {
  const { tasks, activeTask, setActiveTask, cancelTask, isLoading } = useQueueStore()

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'pending':
        return <Clock size={16} className="text-yellow-500" />
      case 'running':
        return <Loader2 size={16} className="text-blue-500 animate-spin" />
      case 'completed':
        return <CheckCircle2 size={16} className="text-green-500" />
      case 'failed':
        return <XCircle size={16} className="text-red-500" />
      case 'cancelled':
        return <X size={16} className="text-gray-400" />
      default:
        return <Clock size={16} className="text-text-muted" />
    }
  }

  const getStatusText = (status: string) => {
    switch (status) {
      case 'pending':
        return '等待中'
      case 'running':
        return '生成中'
      case 'completed':
        return '已完成'
      case 'failed':
        return '失败'
      case 'cancelled':
        return '已取消'
      default:
        return '未知'
    }
  }

  const handleCancel = async (taskId: string) => {
    if (confirm('确定要取消这个任务吗？')) {
      try {
        await cancelTask(taskId)
      } catch (err) {
        console.error('Failed to cancel task:', err)
      }
    }
  }

  if (tasks.length === 0) {
    return (
      <div className="bg-card rounded-xl shadow-md p-6">
        <h3 className="text-lg font-semibold text-text-primary mb-4">任务队列</h3>
        <div className="text-center text-text-muted py-8">
          <Clock size={48} className="mx-auto mb-3 opacity-50" />
          <p className="text-sm">暂无任务</p>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-card rounded-xl shadow-md p-6">
      <h3 className="text-lg font-semibold text-text-primary mb-4">
        任务队列 <span className="text-sm font-normal text-text-muted">({tasks.length})</span>
      </h3>

      <div className="space-y-3 max-h-[600px] overflow-y-auto">
        {tasks.map((task) => (
          <div
            key={task.id}
            onClick={() => setActiveTask(task)}
            className={`p-3 rounded-lg border-2 cursor-pointer transition-all ${
              activeTask?.id === task.id
                ? 'border-primary bg-primary/5'
                : 'border-border hover:border-primary/30'
            }`}
          >
            {/* 头部 */}
            <div className="flex items-start justify-between mb-2">
              <div className="flex items-center gap-2">
                {getStatusIcon(task.status)}
                <span className="text-sm font-medium text-text-primary">
                  {getStatusText(task.status)}
                </span>
              </div>

              {task.status === 'pending' || task.status === 'running' ? (
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    handleCancel(task.id)
                  }}
                  disabled={isLoading}
                  className="p-1 text-text-muted hover:text-red-500 hover:bg-red-50 rounded transition-colors"
                  title="取消任务"
                >
                  <X size={14} />
                </button>
              ) : task.status === 'completed' && task.article_id ? (
                <a
                  href={`/history?article=${task.article_id}`}
                  onClick={(e) => e.stopPropagation()}
                  className="p-1 text-text-muted hover:text-primary hover:bg-primary/10 rounded transition-colors"
                  title="查看文章"
                >
                  <FileText size={14} />
                </a>
              ) : null}
            </div>

            {/* 主题 */}
            <p className="text-sm text-text-primary line-clamp-2 mb-2">
              {task.topic}
            </p>

            {/* 进度条 */}
            {(task.status === 'running' || task.status === 'pending') && (
              <div className="mb-2">
                <div className="flex items-center justify-between text-xs text-text-muted mb-1">
                  <span>进度</span>
                  <span>{task.progress}%</span>
                </div>
                <div className="w-full bg-background rounded-full h-1.5 overflow-hidden">
                  <div
                    className="bg-primary h-full transition-all duration-300"
                    style={{ width: `${task.progress}%` }}
                  />
                </div>
              </div>
            )}

            {/* 进度文本 */}
            {task.progress_text && (
              <p className="text-xs text-text-muted line-clamp-1 mb-2">
                {task.progress_text}
              </p>
            )}

            {/* 实时预览 */}
            {task.live_article && task.status === 'running' && (
              <div className="mt-2 p-2 bg-background rounded text-xs">
                <div className="font-medium text-text-primary mb-1">实时预览:</div>
                <div className="text-text-muted line-clamp-3 prose prose-xs max-w-none">
                  <ReactMarkdown>{task.live_article}</ReactMarkdown>
                </div>
              </div>
            )}

            {/* 错误信息 */}
            {task.status === 'failed' && task.error_message && (
              <div className="mt-2 p-2 bg-red-50 border border-red-200 rounded text-xs text-red-600">
                {task.error_message}
              </div>
            )}

            {/* 时间 */}
            <p className="text-xs text-text-muted mt-2">
              {formatDistanceToNow(new Date(task.created_at), {
                addSuffix: true,
                locale: zhCN,
              })}
            </p>
          </div>
        ))}
      </div>
    </div>
  )
}

export default QueuePanel
