import { ArticleTask } from '@store/articleStore'
import { Loader2, CheckCircle2, XCircle, FileText, ExternalLink, Search, List, BookOpen, ChevronDown, ChevronRight } from 'lucide-react'
import { useState, useEffect } from 'react'
import { useArticleStore } from '@store/articleStore'
import PublishModal from './PublishModal'
import ReactMarkdown from 'react-markdown'

interface ProgressViewProps {
  task: ArticleTask
}

function ProgressView({ task }: ProgressViewProps) {
  const { loadArticle } = useArticleStore()
  const [showPublishModal, setShowPublishModal] = useState(false)
  const [expandedPanels, setExpandedPanels] = useState<Record<string, boolean>>({})

  const togglePanel = (key: string) => {
    setExpandedPanels(prev => ({ ...prev, [key]: !prev[key] }))
  }

  const statusConfig = {
    pending: {
      icon: <Loader2 size={24} className="text-yellow-500 animate-spin" />,
      title: '任务等待中',
      description: '任务已创建，正在排队等待处理...',
    },
    running: {
      icon: <Loader2 size={24} className="text-primary animate-spin" />,
      title: '文章生成中',
      description: task.progress_text || 'AI 正在努力创作中...',
    },
    completed: {
      icon: <CheckCircle2 size={24} className="text-green-500" />,
      title: '生成完成',
      description: '文章已成功生成！',
    },
    failed: {
      icon: <XCircle size={24} className="text-red-500" />,
      title: '生成失败',
      description: task.error_message || '任务执行失败，请重试',
    },
    cancelled: {
      icon: <XCircle size={24} className="text-text-muted" />,
      title: '已取消',
      description: '任务已被取消',
    },
  }

  const config = statusConfig[task.status]

  useEffect(() => {
    if (task.status === 'completed' && task.article_id) {
      loadArticle(task.article_id).then(() => {})
    }
  }, [task.status, task.article_id])

  const handleViewArticle = async () => {
    if (task.article_id) {
      await loadArticle(task.article_id)
      setShowPublishModal(true)
    }
  }

  const handlePublish = () => {
    setShowPublishModal(true)
  }

  return (
    <>
      <div className="bg-card rounded-xl shadow-md p-6">
        {/* 头部 */}
        <div className="flex items-center gap-4 mb-4">
          <div className="p-3 bg-background rounded-lg">
            {config.icon}
          </div>
          <div className="flex-1">
            <h3 className="text-lg font-semibold text-text-primary">
              {config.title}
            </h3>
            <p className="text-sm text-text-muted">{config.description}</p>
          </div>
        </div>

        {/* 进度条 */}
        {(task.status === 'running' || task.status === 'pending') && (
          <div className="mb-4">
            <div className="flex items-center justify-between text-sm text-text-secondary mb-2">
              <span>生成进度</span>
              <span className="font-medium">{task.progress}%</span>
            </div>
            <div className="w-full bg-background rounded-full h-2 overflow-hidden">
              <div
                className="bg-primary h-full transition-all duration-500 ease-out"
                style={{ width: `${task.progress}%` }}
              />
            </div>
          </div>
        )}

        {/* 搜索详情 */}
        {task.search_results && task.search_results.length > 0 && (
          <div className="mb-3 border border-border rounded-lg overflow-hidden">
            <button
              onClick={() => togglePanel('search')}
              className="w-full flex items-center gap-2 px-4 py-2.5 bg-background hover:bg-background/80 transition-colors text-left"
            >
              <Search size={16} className="text-primary" />
              <span className="text-sm font-medium text-text-primary flex-1">
                搜索详情 ({task.search_results.length} 条结果)
              </span>
              {expandedPanels['search'] ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
            </button>
            {expandedPanels['search'] && (
              <div className="px-4 py-3 max-h-60 overflow-y-auto space-y-2">
                {task.search_results.map((item, idx) => (
                  <div key={idx} className="text-xs">
                    <a
                      href={item.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-primary hover:underline font-medium"
                    >
                      {item.title || item.url}
                    </a>
                    {item.snippet && (
                      <p className="text-text-muted mt-0.5 line-clamp-2">{item.snippet}</p>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* 大纲详情 */}
        {task.outline && (
          <div className="mb-3 border border-border rounded-lg overflow-hidden">
            <button
              onClick={() => togglePanel('outline')}
              className="w-full flex items-center gap-2 px-4 py-2.5 bg-background hover:bg-background/80 transition-colors text-left"
            >
              <List size={16} className="text-primary" />
              <span className="text-sm font-medium text-text-primary flex-1">
                大纲详情
              </span>
              {expandedPanels['outline'] ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
            </button>
            {expandedPanels['outline'] && (
              <div className="px-4 py-3 max-h-60 overflow-y-auto">
                {task.outline.title && (
                  <h4 className="text-sm font-semibold text-text-primary mb-2">{task.outline.title}</h4>
                )}
                {task.outline.summary && (
                  <p className="text-xs text-text-muted mb-3 italic">{task.outline.summary}</p>
                )}
                {task.outline.content_outline?.map((section: any, idx: number) => (
                  <div key={idx} className="mb-2">
                    <p className="text-sm font-medium text-text-primary">
                      {idx + 1}. {section.h1}
                    </p>
                    {section.h2?.map((h2: string, h2Idx: number) => (
                      <p key={h2Idx} className="text-xs text-text-muted ml-4 mt-0.5">
                        • {h2}
                      </p>
                    ))}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* 参考来源 */}
        {task.references && task.references.length > 0 && (
          <div className="mb-3 border border-border rounded-lg overflow-hidden">
            <button
              onClick={() => togglePanel('references')}
              className="w-full flex items-center gap-2 px-4 py-2.5 bg-background hover:bg-background/80 transition-colors text-left"
            >
              <BookOpen size={16} className="text-primary" />
              <span className="text-sm font-medium text-text-primary flex-1">
                参考来源 ({task.references.length} 条)
              </span>
              {expandedPanels['references'] ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
            </button>
            {expandedPanels['references'] && (
              <div className="px-4 py-3 max-h-60 overflow-y-auto space-y-1.5">
                {task.references.map((ref, idx) => (
                  <div key={idx} className="text-xs">
                    <a
                      href={ref.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-primary hover:underline"
                    >
                      {ref.title}
                    </a>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* 实时文章预览 */}
        {task.live_article && (
          <div className="mb-4">
            <h4 className="text-sm font-medium text-text-secondary mb-2">
              实时预览
            </h4>
            <div className="p-4 bg-background rounded-lg max-h-96 overflow-y-auto">
              <div className="prose prose-sm max-w-none">
                <ReactMarkdown>{task.live_article}</ReactMarkdown>
              </div>
            </div>
          </div>
        )}

        {/* 完成后的操作 */}
        {task.status === 'completed' && (
          <div className="flex gap-3">
            <button
              onClick={handleViewArticle}
              className="flex-1 flex items-center justify-center gap-2 bg-primary text-white py-3 rounded-lg font-medium hover:bg-primary-dark transition-colors"
            >
              <FileText size={18} />
              <span>查看并编辑</span>
            </button>

            <button
              onClick={handlePublish}
              className="flex-1 flex items-center justify-center gap-2 bg-cta text-white py-3 rounded-lg font-medium hover:bg-cta-dark transition-colors"
            >
              <ExternalLink size={18} />
              <span>直接发布</span>
            </button>
          </div>
        )}

        {/* 失败后的重试 */}
        {task.status === 'failed' && (
          <button
            onClick={() => window.location.reload()}
            className="w-full bg-primary text-white py-3 rounded-lg font-medium hover:bg-primary-dark transition-colors"
          >
            重新生成
          </button>
        )}

        {/* 主题信息 */}
        <div className="mt-4 pt-4 border-t border-border">
          <p className="text-sm text-text-muted">
            <span className="font-medium">主题：</span>
            {task.topic}
          </p>
          <p className="text-xs text-text-muted mt-1">
            类型: {task.article_type} | 创建时间:{' '}
            {new Date(task.created_at).toLocaleString('zh-CN')}
            {task.article_metadata && (
              <> | 模型: {task.article_metadata.model_type}/{task.article_metadata.model_name}
              {task.article_metadata.spider_num != null && <> | 搜索: {task.article_metadata.spider_num} 条</>}
              {task.article_metadata.total_images != null && <> | 图片: {task.article_metadata.total_images} 张</>}
              </>
            )}
          </p>
        </div>
      </div>

      {/* 发布弹窗 */}
      {showPublishModal && task.article_id && (
        <PublishModal
          articleId={task.article_id}
          onClose={() => setShowPublishModal(false)}
        />
      )}
    </>
  )
}

export default ProgressView
