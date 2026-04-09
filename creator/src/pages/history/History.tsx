import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { FileText, Calendar, Search, Filter, Trash2, Edit, Cpu, Globe, Image } from 'lucide-react'
import { useArticleStore } from '@store/articleStore'
import { formatDistanceToNow } from 'date-fns'
import { zhCN } from 'date-fns/locale'

type ArticleStatus = 'all' | 'draft' | 'published' | 'archived'
type SortBy = 'created_at' | 'updated_at' | 'title' | 'view_count'

function History() {
  const { articles, loadArticles, deleteArticle, isLoading, error } = useArticleStore()

  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState<ArticleStatus>('all')
  const [sortBy, setSortBy] = useState<SortBy>('updated_at')
  const [page, setPage] = useState(1)
  const pageSize = 12

  useEffect(() => {
    loadArticles({
      status: statusFilter === 'all' ? undefined : statusFilter,
      page,
      page_size: pageSize,
    })
  }, [statusFilter, page])

  const handleDelete = async (articleId: number) => {
    if (confirm('确定要删除这篇文章吗？此操作不可恢复。')) {
      try {
        await deleteArticle(articleId)
        // 重新加载列表
        loadArticles({
          status: statusFilter === 'all' ? undefined : statusFilter,
          page,
          page_size: pageSize,
        })
      } catch (err) {
        console.error('Failed to delete article:', err)
      }
    }
  }

  const getStatusBadge = (status: string) => {
    const badges = {
      draft: { label: '草稿', color: 'bg-gray-100 text-gray-600' },
      published: { label: '已发布', color: 'bg-green-100 text-green-600' },
      archived: { label: '已归档', color: 'bg-yellow-100 text-yellow-600' },
    }
    const badge = badges[status as keyof typeof badges] || badges.draft
    return (
      <span className={`px-2 py-1 rounded-full text-xs font-medium ${badge.color}`}>
        {badge.label}
      </span>
    )
  }

  // 过滤和排序
  const filteredArticles = articles
    .filter((article) => {
      if (searchQuery) {
        const query = searchQuery.toLowerCase()
        return (
          article.title.toLowerCase().includes(query) ||
          article.content?.toLowerCase().includes(query) ||
          article.tags?.some((tag) => tag.toLowerCase().includes(query))
        )
      }
      return true
    })
    .sort((a, b) => {
      switch (sortBy) {
        case 'created_at':
          return new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
        case 'updated_at':
          return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
        case 'title':
          return a.title.localeCompare(b.title, 'zh-CN')
        case 'view_count':
          return b.view_count - a.view_count
        default:
          return 0
      }
    })

  return (
    <div className="space-y-6">
      {/* 头部 */}
      <div>
        <h1 className="text-3xl font-bold text-text-primary">历史记录</h1>
        <p className="text-text-muted mt-1">查看和管理您的所有文章</p>
      </div>

      {/* 错误提示 */}
      {error && (
        <div className="p-4 bg-red-50 border border-red-200 text-red-600 rounded-lg">
          {error}
        </div>
      )}

      {/* 搜索和筛选 */}
      <div className="bg-card rounded-xl shadow-md p-6">
        <div className="flex flex-col md:flex-row gap-4">
          {/* 搜索框 */}
          <div className="flex-1 relative">
            <Search
              size={20}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted"
            />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="搜索文章标题、内容或标签..."
              className="w-full pl-10 pr-4 py-2 rounded-lg border border-border focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
            />
          </div>

          {/* 状态筛选 */}
          <div className="flex items-center gap-2">
            <Filter size={20} className="text-text-muted" />
            <select
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value as ArticleStatus)
                setPage(1)
              }}
              className="px-4 py-2 rounded-lg border border-border focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
            >
              <option value="all">全部状态</option>
              <option value="draft">草稿</option>
              <option value="published">已发布</option>
              <option value="archived">已归档</option>
            </select>
          </div>

          {/* 排序 */}
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as SortBy)}
            className="px-4 py-2 rounded-lg border border-border focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
          >
            <option value="updated_at">最新更新</option>
            <option value="created_at">创建时间</option>
            <option value="title">标题排序</option>
            <option value="view_count">浏览量</option>
          </select>
        </div>
      </div>

      {/* 文章列表 */}
      {isLoading && articles.length === 0 ? (
        <div className="bg-card rounded-xl shadow-md p-12 text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4" />
          <p className="text-text-muted">加载中...</p>
        </div>
      ) : filteredArticles.length === 0 ? (
        <div className="bg-card rounded-xl shadow-md p-12 text-center">
          <FileText size={48} className="text-text-muted mx-auto mb-4" />
          <p className="text-text-muted">
            {searchQuery ? '没有找到匹配的文章' : '还没有文章，去创建第一篇吧！'}
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredArticles.map((article) => (
            <div
              key={article.id}
              className="bg-card rounded-xl shadow-md overflow-hidden hover:shadow-lg transition-all hover:-translate-y-1 group"
            >
              {/* 封面图 */}
              {article.cover_image && (
                <div className="aspect-video overflow-hidden">
                  <img
                    src={article.cover_image}
                    alt={article.title}
                    className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                  />
                </div>
              )}

              {/* 内容 */}
              <div className="p-5">
                {/* 状态标签 */}
                <div className="flex items-center justify-between mb-3">
                  {getStatusBadge(article.status)}
                  <div className="flex items-center gap-2 text-xs text-text-muted">
                    <Calendar size={14} />
                    <span>
                      {formatDistanceToNow(new Date(article.updated_at), {
                        addSuffix: true,
                        locale: zhCN,
                      })}
                    </span>
                  </div>
                </div>

                {/* 标题 */}
                <h3 className="text-lg font-semibold text-text-primary mb-2 line-clamp-2 group-hover:text-primary transition-colors">
                  <Link to={`/history/${article.id}`}>{article.title}</Link>
                </h3>

                {/* 摘要 */}
                <p className="text-sm text-text-muted line-clamp-2 mb-3">
                  {article.content?.substring(0, 100).replace(/[#*`]/g, '')}...
                </p>

                {/* 标签 */}
                {article.tags && article.tags.length > 0 && (
                  <div className="flex flex-wrap gap-1 mb-3">
                    {article.tags.slice(0, 3).map((tag) => (
                      <span
                        key={tag}
                        className="text-xs px-2 py-0.5 bg-primary/10 text-primary rounded-full"
                      >
                        #{tag}
                      </span>
                    ))}
                    {article.tags.length > 3 && (
                      <span className="text-xs px-2 py-0.5 bg-background text-text-muted rounded-full">
                        +{article.tags.length - 3}
                      </span>
                    )}
                  </div>
                )}

                {/* 生成参数 */}
                {article.metadata && Object.keys(article.metadata).length > 0 && (
                  <div className="flex flex-wrap items-center gap-3 text-xs text-text-muted mb-4">
                    {(article.metadata.model_type || article.metadata.model_name) && (
                      <div className="flex items-center gap-1">
                        <Cpu size={12} />
                        <span>{article.metadata.model_name || article.metadata.model_type}</span>
                      </div>
                    )}
                    {article.metadata.spider_num != null && (
                      <div className="flex items-center gap-1">
                        <Globe size={12} />
                        <span>{article.metadata.spider_num} 条搜索</span>
                      </div>
                    )}
                    {article.metadata.total_images != null && (
                      <div className="flex items-center gap-1">
                        <Image size={12} />
                        <span>{article.metadata.total_images} 张图片</span>
                      </div>
                    )}
                  </div>
                )}

                {/* 操作按钮 */}
                <div className="flex gap-2">
                  <Link
                    to={`/writer?article=${article.id}`}
                    className="flex-1 flex items-center justify-center gap-2 px-3 py-2 bg-primary text-white rounded-lg text-sm font-medium hover:bg-primary-dark transition-colors"
                  >
                    <Edit size={16} />
                    <span>编辑</span>
                  </Link>

                  <button
                    onClick={() => handleDelete(article.id)}
                    className="p-2 text-text-muted hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
                    title="删除"
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* 分页 */}
      {filteredArticles.length > pageSize && (
        <div className="flex justify-center items-center gap-2">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="px-4 py-2 bg-card border border-border rounded-lg hover:border-primary transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            上一页
          </button>

          <span className="text-text-muted">
            第 {page} 页
          </span>

          <button
            onClick={() => setPage((p) => p + 1)}
            disabled={articles.length < pageSize}
            className="px-4 py-2 bg-card border border-border rounded-lg hover:border-primary transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            下一页
          </button>
        </div>
      )}
    </div>
  )
}

export default History
