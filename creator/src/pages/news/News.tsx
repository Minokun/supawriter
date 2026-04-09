import { useEffect, useState } from 'react'
import { Newspaper, ExternalLink, RefreshCw, Clock, Tag } from 'lucide-react'
import { newsAPI } from '@lib/api'
import { formatDistanceToNow } from 'date-fns'
import { zhCN } from 'date-fns/locale'

interface NewsArticle {
  id: string
  title: string
  description: string
  url: string
  source: string
  category: string
  author: string | null
  published_at: string
  image_url: string | null
}

interface CategoryInfo {
  id: string
  name: string
  icon: string
}

const categories: CategoryInfo[] = [
  { id: 'all', name: '全部', icon: '📰' },
  { id: 'tech', name: '科技', icon: '💻' },
  { id: 'business', name: '商业', icon: '💼' },
  { id: 'entertainment', name: '娱乐', icon: '🎬' },
  { id: 'sports', name: '体育', icon: '⚽' },
  { id: 'health', name: '健康', icon: '🏥' },
  { id: 'science', name: '科学', icon: '🔬' },
]

function News() {
  const [articles, setArticles] = useState<NewsArticle[]>([])
  const [selectedCategory, setSelectedCategory] = useState<string>('all')
  const [selectedSource, setSelectedSource] = useState<string>('all')
  const [sources, setSources] = useState<string[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const loadNews = async () => {
    try {
      setIsLoading(true)
      setError(null)

      // 加载来源列表
      if (sources.length === 0) {
        try {
          const sourcesData = await newsAPI.getSources()
          setSources(sourcesData || [])
        } catch (err) {
          console.error('Failed to load sources:', err)
        }
      }

      // 加载新闻
      const params: any = {}
      if (selectedCategory !== 'all') params.category = selectedCategory
      if (selectedSource !== 'all') params.source = selectedSource

      const data = await newsAPI.getAll(params)
      setArticles(data || [])
    } catch (err) {
      console.error('Failed to load news:', err)
      setError('加载新闻失败，请稍后重试')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    loadNews()
  }, [selectedCategory, selectedSource])

  const getCategoryName = (categoryId: string) => {
    const category = categories.find((c) => c.id === categoryId)
    return category?.name || categoryId
  }

  return (
    <div className="space-y-6">
      {/* 头部 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-text-primary">新闻资讯</h1>
          <p className="text-text-muted mt-1">获取最新资讯，了解行业动态</p>
        </div>

        <button
          onClick={loadNews}
          disabled={isLoading}
          className="flex items-center gap-2 px-4 py-2 bg-card border border-border rounded-lg hover:border-primary transition-colors disabled:opacity-50"
        >
          <RefreshCw size={18} className={isLoading ? 'animate-spin' : ''} />
          <span>刷新</span>
        </button>
      </div>

      {/* 错误提示 */}
      {error && (
        <div className="p-4 bg-red-50 border border-red-200 text-red-600 rounded-lg">
          {error}
        </div>
      )}

      {/* 筛选栏 */}
      <div className="bg-card rounded-xl shadow-md p-6">
        {/* 分类筛选 */}
        <div className="mb-4">
          <h3 className="text-sm font-medium text-text-secondary mb-3">分类</h3>
          <div className="flex flex-wrap gap-2">
            {categories.map((category) => (
              <button
                key={category.id}
                onClick={() => setSelectedCategory(category.id)}
                className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                  selectedCategory === category.id
                    ? 'bg-primary text-white'
                    : 'bg-background text-text-secondary hover:text-primary'
                }`}
              >
                <span className="mr-1">{category.icon}</span>
                {category.name}
              </button>
            ))}
          </div>
        </div>

        {/* 来源筛选 */}
        {sources.length > 0 && (
          <div>
            <h3 className="text-sm font-medium text-text-secondary mb-3">来源</h3>
            <div className="flex flex-wrap gap-2">
              <button
                onClick={() => setSelectedSource('all')}
                className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                  selectedSource === 'all'
                    ? 'bg-primary text-white'
                    : 'bg-background text-text-secondary hover:text-primary'
                }`}
              >
                全部来源
              </button>

              {sources.map((source) => (
                <button
                  key={source}
                  onClick={() => setSelectedSource(source)}
                  className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                    selectedSource === source
                      ? 'bg-primary text-white'
                      : 'bg-background text-text-secondary hover:text-primary'
                  }`}
                >
                  {source}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* 新闻列表 */}
      {isLoading && articles.length === 0 ? (
        <div className="bg-card rounded-xl shadow-md p-12 text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4" />
          <p className="text-text-muted">加载中...</p>
        </div>
      ) : articles.length === 0 ? (
        <div className="bg-card rounded-xl shadow-md p-12 text-center">
          <Newspaper size={48} className="text-text-muted mx-auto mb-4" />
          <p className="text-text-muted">暂无新闻数据</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {articles.map((article) => (
            <article
              key={article.id}
              className="bg-card rounded-xl shadow-md overflow-hidden hover:shadow-lg transition-all hover:-translate-y-1 group"
            >
              {/* 图片 */}
              {article.image_url && (
                <div className="aspect-video overflow-hidden">
                  <img
                    src={article.image_url}
                    alt={article.title}
                    className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                  />
                </div>
              )}

              {/* 内容 */}
              <div className="p-5">
                {/* 分类和来源 */}
                <div className="flex items-center gap-2 mb-3">
                  <span className="text-xs px-2 py-1 bg-primary/10 text-primary rounded-full">
                    {getCategoryName(article.category)}
                  </span>
                  <span className="text-xs text-text-muted">·</span>
                  <span className="text-xs text-text-muted">{article.source}</span>
                </div>

                {/* 标题 */}
                <h3 className="text-lg font-semibold text-text-primary mb-2 line-clamp-2 group-hover:text-primary transition-colors">
                  {article.title}
                </h3>

                {/* 摘要 */}
                {article.description && (
                  <p className="text-sm text-text-muted line-clamp-3 mb-3">
                    {article.description}
                  </p>
                )}

                {/* 元信息 */}
                <div className="flex items-center justify-between text-xs text-text-muted">
                  <div className="flex items-center gap-1">
                    <Clock size={14} />
                    <span>
                      {formatDistanceToNow(new Date(article.published_at), {
                        addSuffix: true,
                        locale: zhCN,
                      })}
                    </span>
                  </div>

                  {article.url && (
                    <a
                      href={article.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-1 text-primary hover:underline"
                    >
                      阅读原文
                      <ExternalLink size={12} />
                    </a>
                  )}
                </div>
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  )
}

export default News
