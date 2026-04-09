import { useEffect, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { useQueueStore } from '@store/queueStore'
import { useArticleStore } from '@store/articleStore'
import { PenTool, Sparkles, Clock, TrendingUp } from 'lucide-react'
import QueuePanel from './QueuePanel'
import ProgressView from './ProgressView'
import { useAuthStore } from '@store/authStore'

type ArticleType = 'news' | 'blog' | 'social_media' | 'academic' | 'creative'

interface ArticleTypeInfo {
  id: ArticleType
  name: string
  description: string
  icon: React.ElementType
  color: string
}

const articleTypes: ArticleTypeInfo[] = [
  {
    id: 'news',
    name: '新闻报道',
    description: '客观、及时地报道新闻事件',
    icon: TrendingUp,
    color: 'bg-blue-100 text-blue-600',
  },
  {
    id: 'blog',
    name: '博客文章',
    description: '分享观点、经验或教程',
    icon: PenTool,
    color: 'bg-green-100 text-green-600',
  },
  {
    id: 'social_media',
    name: '社交媒体',
    description: '简短有力的社交媒体内容',
    icon: Sparkles,
    color: 'bg-purple-100 text-purple-600',
  },
  {
    id: 'academic',
    name: '学术论文',
    description: '严谨的学术写作',
    icon: Clock,
    color: 'bg-orange-100 text-orange-600',
  },
  {
    id: 'creative',
    name: '创意写作',
    description: '小说、诗歌等创意内容',
    icon: Sparkles,
    color: 'bg-pink-100 text-pink-600',
  },
]

function Writer() {
  const location = useLocation()
  const { user } = useAuthStore()
  const { tasks, activeTask, loadQueue, connectWebSocket } = useQueueStore()
  const { generateArticle, isLoading, error, clearError } = useArticleStore()

  const [topic, setTopic] = useState('')
  const [selectedType, setSelectedType] = useState<ArticleType>('blog')
  const [customStyle, setCustomStyle] = useState('')
  const [showQueue, setShowQueue] = useState(false)
  const [prefillApplied, setPrefillApplied] = useState(false)

  useEffect(() => {
    loadQueue()
    if (user?.id) {
      connectWebSocket(user.id.toString())
    }
  }, [user])

  useEffect(() => {
    if (prefillApplied) return
    const state = location.state as { topic?: string; customStyle?: string; articleType?: ArticleType } | null
    if (!state) return

    if (state.topic) setTopic(state.topic)
    if (state.customStyle) setCustomStyle(state.customStyle)
    if (state.articleType) setSelectedType(state.articleType)

    if (state.topic || state.customStyle || state.articleType) {
      setPrefillApplied(true)
    }
  }, [location.state, prefillApplied])

  const handleGenerate = async () => {
    if (!topic.trim()) {
      alert('请输入文章主题')
      return
    }

    try {
      const taskId = await generateArticle({
        topic: topic.trim(),
        article_type: selectedType,
        custom_style: customStyle.trim() || undefined,
      })

      // 添加任务到队列
      const newTask = {
        id: taskId,
        user_id: user!.id,
        topic: topic.trim(),
        article_type: selectedType,
        custom_style: customStyle.trim() || null,
        status: 'pending' as const,
        progress: 0,
        progress_text: '任务已创建，等待处理...',
        live_article: null,
        error_message: null,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        completed_at: null,
        article_id: null,
      }

      useQueueStore.getState().addTask(newTask)
      useQueueStore.getState().setActiveTask(newTask)

      // 重置表单
      setTopic('')
      setCustomStyle('')

      // 切换到进度视图
      setShowQueue(true)
    } catch (err) {
      console.error('Failed to generate article:', err)
    }
  }

  return (
    <div className="space-y-6">
      {/* 头部 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-text-primary">超能写手</h1>
          <p className="text-text-muted mt-1">使用 AI 技术快速生成高质量文章</p>
        </div>

        <button
          onClick={() => setShowQueue(!showQueue)}
          className="flex items-center gap-2 px-4 py-2 bg-card border border-border rounded-lg hover:border-primary transition-colors"
        >
          <Clock size={18} />
          <span>{showQueue ? '隐藏' : '显示'}队列</span>
          {tasks.length > 0 && (
            <span className="ml-1 px-2 py-0.5 bg-primary text-white text-xs rounded-full">
              {tasks.length}
            </span>
          )}
        </button>
      </div>

      {/* 错误提示 */}
      {error && (
        <div className="p-4 bg-red-50 border border-red-200 text-red-600 rounded-lg flex items-center justify-between">
          <span>{error}</span>
          <button onClick={clearError} className="text-red-800 hover:text-red-900">
            ✕
          </button>
        </div>
      )}

      {/* 主内容区 */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 左侧：生成表单 */}
        <div className={`lg:col-span-${showQueue ? '2' : '3'}`}>
          <div className="bg-card rounded-xl shadow-md p-6">
            <h2 className="text-xl font-semibold text-text-primary mb-6">创建新文章</h2>

            {/* 文章主题 */}
            <div className="mb-6">
              <label className="block text-sm font-medium text-text-primary mb-2">
                文章主题 <span className="text-red-500">*</span>
              </label>
              <textarea
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                placeholder="请输入您想要撰写的文章主题..."
                rows={4}
                className="w-full px-4 py-3 rounded-lg border border-border focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent resize-none"
                disabled={isLoading}
              />
              <p className="text-xs text-text-muted mt-1">
                {topic.length} / 500 字符
              </p>
            </div>

            {/* 文章类型 */}
            <div className="mb-6">
              <label className="block text-sm font-medium text-text-primary mb-3">
                文章类型
              </label>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                {articleTypes.map((type) => {
                  const Icon = type.icon
                  return (
                    <button
                      key={type.id}
                      onClick={() => setSelectedType(type.id)}
                      className={`p-4 rounded-lg border-2 transition-all text-left ${
                        selectedType === type.id
                          ? 'border-primary bg-primary/5'
                          : 'border-border hover:border-primary/50'
                      }`}
                      disabled={isLoading}
                    >
                      <div className={`p-2 rounded-lg ${type.color} mb-2`}>
                        <Icon size={20} />
                      </div>
                      <h3 className="font-medium text-sm text-text-primary">
                        {type.name}
                      </h3>
                      <p className="text-xs text-text-muted mt-1">
                        {type.description}
                      </p>
                    </button>
                  )
                })}
              </div>
            </div>

            {/* 自定义风格 */}
            <div className="mb-6">
              <label className="block text-sm font-medium text-text-primary mb-2">
                自定义风格 <span className="text-text-muted">(可选)</span>
              </label>
              <textarea
                value={customStyle}
                onChange={(e) => setCustomStyle(e.target.value)}
                placeholder="例如：使用幽默的语气、引用数据和案例、面向技术读者等..."
                rows={3}
                className="w-full px-4 py-3 rounded-lg border border-border focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent resize-none"
                disabled={isLoading}
              />
              <p className="text-xs text-text-muted mt-1">
                {customStyle.length} / 300 字符
              </p>
            </div>

            {/* 生成按钮 */}
            <button
              onClick={handleGenerate}
              disabled={!topic.trim() || isLoading}
              className="w-full bg-primary text-white py-4 rounded-lg font-medium hover:bg-primary-dark transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              <PenTool size={20} />
              <span>
                {isLoading ? '创建中...' : '开始生成文章'}
              </span>
            </button>

            <p className="text-xs text-text-muted text-center mt-3">
              预计生成时间 1-3 分钟，请在队列中查看进度
            </p>
          </div>

          {/* 当前任务进度 */}
          {activeTask && (
            <div className="mt-6">
              <ProgressView task={activeTask} />
            </div>
          )}
        </div>

        {/* 右侧：队列面板 */}
        {showQueue && (
          <div className="lg:col-span-1">
            <QueuePanel />
          </div>
        )}
      </div>
    </div>
  )
}

export default Writer
