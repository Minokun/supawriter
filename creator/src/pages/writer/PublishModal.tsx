import { useState, useEffect } from 'react'
import { useArticleStore } from '@store/articleStore'
import { X, Globe, Tag, Image as ImageIcon } from 'lucide-react'

interface PublishModalProps {
  articleId: number
  onClose: () => void
}

function PublishModal({ articleId, onClose }: PublishModalProps) {
  const { currentArticle, publishArticle, loadArticle, isLoading, error } =
    useArticleStore()

  const [seoTitle, setSeoTitle] = useState('')
  const [seoDesc, setSeoDesc] = useState('')
  const [tags, setTags] = useState<string[]>([])
  const [tagInput, setTagInput] = useState('')

  useEffect(() => {
    if (articleId) {
      loadArticle(articleId)
    }
  }, [articleId])

  useEffect(() => {
    if (currentArticle) {
      setSeoTitle(currentArticle.seo_title || currentArticle.title || '')
      setSeoDesc(currentArticle.seo_desc || '')
      setTags(currentArticle.tags || [])
    }
  }, [currentArticle])

  const handleAddTag = () => {
    const tag = tagInput.trim()
    if (tag && !tags.includes(tag)) {
      setTags([...tags, tag])
      setTagInput('')
    }
  }

  const handleRemoveTag = (tagToRemove: string) => {
    setTags(tags.filter((t) => t !== tagToRemove))
  }

  const handlePublish = async () => {
    try {
      await publishArticle(articleId, {
        seo_title: seoTitle,
        seo_desc: seoDesc,
        tags,
      })

      alert('文章发布成功！')

      // 打开社区网站预览
      if (currentArticle?.slug) {
        window.open(`http://localhost:3001/articles/${currentArticle.slug}`, '_blank')
      }

      onClose()
    } catch (err) {
      console.error('Failed to publish article:', err)
    }
  }

  if (!currentArticle) {
    return (
      <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
        <div className="bg-card rounded-xl p-6 max-w-md w-full mx-4">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4" />
            <p className="text-text-muted">加载文章数据...</p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-card rounded-xl shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        {/* 头部 */}
        <div className="sticky top-0 bg-card border-b border-border px-6 py-4 flex items-center justify-between">
          <h2 className="text-xl font-semibold text-text-primary">发布文章</h2>
          <button
            onClick={onClose}
            className="p-2 hover:bg-background rounded-lg transition-colors"
          >
            <X size={20} className="text-text-muted" />
          </button>
        </div>

        {/* 内容 */}
        <div className="p-6 space-y-6">
          {/* 错误提示 */}
          {error && (
            <div className="p-3 bg-red-50 border border-red-200 text-red-600 rounded-lg text-sm">
              {error}
            </div>
          )}

          {/* 文章预览 */}
          <div>
            <h3 className="text-sm font-medium text-text-primary mb-2">文章预览</h3>
            <div className="p-4 bg-background rounded-lg">
              <h4 className="text-lg font-semibold text-text-primary mb-2">
                {currentArticle.title}
              </h4>
              <p className="text-sm text-text-muted line-clamp-3">
                {currentArticle.content?.substring(0, 200)}...
              </p>
            </div>
          </div>

          {/* SEO 标题 */}
          <div>
            <label className="flex items-center gap-2 text-sm font-medium text-text-primary mb-2">
              <Globe size={16} />
              SEO 标题
            </label>
            <input
              type="text"
              value={seoTitle}
              onChange={(e) => setSeoTitle(e.target.value)}
              placeholder="用于搜索引擎的标题（默认使用文章标题）"
              className="w-full px-4 py-2 rounded-lg border border-border focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
              maxLength={100}
            />
            <p className="text-xs text-text-muted mt-1">
              {seoTitle.length} / 100 字符
            </p>
          </div>

          {/* SEO 描述 */}
          <div>
            <label className="flex items-center gap-2 text-sm font-medium text-text-primary mb-2">
              <Globe size={16} />
              SEO 描述
            </label>
            <textarea
              value={seoDesc}
              onChange={(e) => setSeoDesc(e.target.value)}
              placeholder="用于搜索引擎的描述（默认使用文章摘要）"
              rows={3}
              className="w-full px-4 py-2 rounded-lg border border-border focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent resize-none"
              maxLength={300}
            />
            <p className="text-xs text-text-muted mt-1">
              {seoDesc.length} / 300 字符
            </p>
          </div>

          {/* 标签 */}
          <div>
            <label className="flex items-center gap-2 text-sm font-medium text-text-primary mb-2">
              <Tag size={16} />
              文章标签
            </label>
            <div className="flex gap-2 mb-2">
              <input
                type="text"
                value={tagInput}
                onChange={(e) => setTagInput(e.target.value)}
                onKeyPress={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault()
                    handleAddTag()
                  }
                }}
                placeholder="输入标签后按回车添加"
                className="flex-1 px-4 py-2 rounded-lg border border-border focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
              />
              <button
                onClick={handleAddTag}
                className="px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary-dark transition-colors"
              >
                添加
              </button>
            </div>
            <div className="flex flex-wrap gap-2">
              {tags.map((tag) => (
                <span
                  key={tag}
                  className="inline-flex items-center gap-1 px-3 py-1 bg-primary/10 text-primary rounded-full text-sm"
                >
                  {tag}
                  <button
                    onClick={() => handleRemoveTag(tag)}
                    className="hover:bg-primary/20 rounded-full p-0.5"
                  >
                    <X size={14} />
                  </button>
                </span>
              ))}
            </div>
          </div>

          {/* 提示 */}
          <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg">
            <p className="text-sm text-blue-800">
              发布后文章将在社区网站公开显示，可以被搜索引擎收录。确认发布吗？
            </p>
          </div>
        </div>

        {/* 底部操作 */}
        <div className="sticky bottom-0 bg-card border-t border-border px-6 py-4 flex gap-3">
          <button
            onClick={onClose}
            disabled={isLoading}
            className="flex-1 px-6 py-3 border border-border rounded-lg font-medium hover:bg-background transition-colors disabled:opacity-50"
          >
            取消
          </button>
          <button
            onClick={handlePublish}
            disabled={isLoading || !seoTitle.trim()}
            className="flex-1 px-6 py-3 bg-primary text-white rounded-lg font-medium hover:bg-primary-dark transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? '发布中...' : '确认发布'}
          </button>
        </div>
      </div>
    </div>
  )
}

export default PublishModal
