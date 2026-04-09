import Link from 'next/link'
import { Calendar, Eye, Search } from 'lucide-react'

interface Article {
  id: number
  title: string
  slug: string
  content: string
  cover_image: string | null
  status: string
  seo_title: string | null
  seo_desc: string | null
  tags: string[]
  view_count: number
  created_at: string
  published_at: string
}

export const metadata = {
  title: '文章列表 - 超能写手社区',
  description: '浏览所有优质文章，探索创作灵感',
}

async function getArticles(page: number, pageSize: number) {
  try {
    const res = await fetch(
      `http://localhost:8000/api/v1/articles?status=published&page=${page}&page_size=${pageSize}`,
      { next: { revalidate: 60 } }
    )

    if (!res.ok) {
      return { articles: [], error: 'Failed to fetch' }
    }

    const articles: Article[] = await res.json()
    return { articles, error: null }
  } catch (error) {
    return { articles: [], error: 'Failed to fetch' }
  }
}

export default async function ArticlesPage({
  searchParams,
}: {
  searchParams: { page?: string; tag?: string }
}) {
  const page = parseInt(searchParams.page || '1')
  const pageSize = 12

  const { articles, error } = await getArticles(page, pageSize)
  const hasMore = articles.length === pageSize

  // Error state
  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <p className="text-text-muted mb-4">加载文章失败</p>
          <Link href="/" className="text-primary hover:underline">
            返回首页
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background">
      {/* 导航栏 */}
      <header className="bg-card border-b border-border sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <Link href="/" className="flex items-center gap-2">
              <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center">
                <span className="text-white font-bold">超</span>
              </div>
              <span className="text-xl font-bold text-primary">超能写手社区</span>
            </Link>

            <nav className="hidden md:flex items-center space-x-8">
              <Link href="/" className="text-text-secondary hover:text-primary transition-colors">
                首页
              </Link>
              <Link href="/articles" className="text-primary font-medium">
                文章
              </Link>
              <Link href="/tags" className="text-text-secondary hover:text-primary transition-colors">
                标签
              </Link>
              <Link href="/search" className="text-text-secondary hover:text-primary transition-colors">
                搜索
              </Link>
            </nav>

            <div className="flex items-center gap-3">
              <Link
                href="http://localhost:3000"
                className="px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary-dark transition-colors text-sm font-medium"
              >
                创作工具
              </Link>
            </div>
          </div>
        </div>
      </header>

      {/* 主内容 */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* 页面标题 */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-text-primary mb-2">文章列表</h1>
          <p className="text-text-secondary">探索和发现优质内容</p>
        </div>

        {/* 搜索框 */}
        <div className="mb-8">
          <Link
            href="/search"
            className="flex items-center gap-3 px-4 py-3 bg-card border border-border rounded-lg hover:border-primary transition-colors"
          >
            <Search size={20} className="text-text-muted" />
            <span className="text-text-muted">搜索文章...</span>
          </Link>
        </div>

        {/* 文章列表 */}
        {articles.length === 0 ? (
          <div className="text-center py-20">
            <div className="inline-block p-6 bg-card rounded-full mb-4">
              📝
            </div>
            <h2 className="text-xl font-semibold text-text-primary mb-2">暂无文章</h2>
            <p className="text-text-muted mb-6">还没有发布的文章</p>
            <Link
              href="http://localhost:3000"
              className="inline-block px-6 py-3 bg-primary text-white rounded-lg hover:bg-primary-dark transition-colors"
            >
              去创作第一篇文章
            </Link>
          </div>
        ) : (
          <>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
              {articles.map((article) => (
                <Link
                  key={article.id}
                  href={`/articles/${article.slug || article.id}`}
                  className="group"
                >
                  <article className="bg-card rounded-xl shadow-md overflow-hidden hover:shadow-lg transition-all hover:-translate-y-1">
                    {article.cover_image && (
                      <div className="aspect-video overflow-hidden">
                        <img
                          src={article.cover_image}
                          alt={article.title}
                          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                        />
                      </div>
                    )}

                    <div className="p-5">
                      {/* 标签 */}
                      {article.tags && article.tags.length > 0 && (
                        <div className="flex flex-wrap gap-2 mb-3">
                          {article.tags.slice(0, 3).map((tag) => (
                            <span
                              key={tag}
                              className="text-xs px-2 py-1 bg-primary/10 text-primary rounded-full"
                            >
                              #{tag}
                            </span>
                          ))}
                        </div>
                      )}

                      {/* 标题 */}
                      <h3 className="text-lg font-semibold text-text-primary mb-2 line-clamp-2 group-hover:text-primary transition-colors">
                        {article.title}
                      </h3>

                      {/* 摘要 */}
                      <p className="text-sm text-text-muted line-clamp-3 mb-4">
                        {article.content?.substring(0, 150).replace(/[#*`]/g, '')}...
                      </p>

                      {/* 元信息 */}
                      <div className="flex items-center justify-between text-xs text-text-muted">
                        <div className="flex items-center gap-1">
                          <Calendar size={14} />
                          <span>
                            {new Date(article.published_at || article.created_at).toLocaleDateString('zh-CN')}
                          </span>
                        </div>
                        <div className="flex items-center gap-1">
                          <Eye size={14} />
                          <span>{article.view_count || 0}</span>
                        </div>
                      </div>
                    </div>
                  </article>
                </Link>
              ))}
            </div>

            {/* 分页 */}
            <div className="flex justify-center items-center gap-4">
              {page > 1 && (
                <Link
                  href={`/articles?page=${page - 1}`}
                  className="px-6 py-2 bg-card border border-border rounded-lg hover:border-primary transition-colors"
                >
                  上一页
                </Link>
              )}

              <span className="text-text-muted">
                第 {page} 页
              </span>

              {hasMore && (
                <Link
                  href={`/articles?page=${page + 1}`}
                  className="px-6 py-2 bg-card border border-border rounded-lg hover:border-primary transition-colors"
                >
                  下一页
                </Link>
              )}
            </div>
          </>
        )}
      </main>

      {/* 页脚 */}
      <footer className="bg-card border-t border-border py-8 mt-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col md:flex-row items-center justify-between">
            <p className="text-text-muted text-sm">
              © 2025 超能写手社区. All rights reserved.
            </p>
          </div>
        </div>
      </footer>
    </div>
  )
}
