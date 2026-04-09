import Link from 'next/link'
import { FileText, TrendingUp, Users, Search } from 'lucide-react'

async function getFeaturedArticles() {
  try {
    const res = await fetch('http://localhost:8000/api/v1/articles?status=published&limit=6', {
      next: { revalidate: 60 }
    })
    if (!res.ok) return []
    return await res.json()
  } catch {
    return []
  }
}

export default async function HomePage() {
  const articles = await getFeaturedArticles()

  return (
    <div className="min-h-screen">
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
              <Link href="/articles" className="text-text-secondary hover:text-primary transition-colors">
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

      {/* Hero 区域 */}
      <section className="bg-gradient-to-r from-primary/10 to-background py-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h1 className="text-5xl md:text-6xl font-bold text-text-primary mb-6">
            AI 驱动的创作社区
          </h1>
          <p className="text-xl text-text-secondary mb-8 max-w-2xl mx-auto">
            探索优质文章，分享创作灵感，与创作者一起成长
          </p>
          <div className="flex items-center justify-center gap-4">
            <Link
              href="/articles"
              className="px-8 py-3 bg-primary text-white rounded-lg font-medium hover:bg-primary-dark transition-colors"
            >
              浏览文章
            </Link>
            <Link
              href="http://localhost:3000"
              className="px-8 py-3 border-2 border-primary text-primary rounded-lg font-medium hover:bg-primary/10 transition-colors"
            >
              开始创作
            </Link>
          </div>
        </div>
      </section>

      {/* 统计数据 */}
      <section className="py-12 bg-card">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="text-center">
              <div className="flex items-center justify-center gap-2 mb-2">
                <FileText className="text-primary" size={32} />
                <span className="text-4xl font-bold text-text-primary">1000+</span>
              </div>
              <p className="text-text-secondary">优质文章</p>
            </div>
            <div className="text-center">
              <div className="flex items-center justify-center gap-2 mb-2">
                <Users className="text-primary" size={32} />
                <span className="text-4xl font-bold text-text-primary">500+</span>
              </div>
              <p className="text-text-secondary">活跃创作者</p>
            </div>
            <div className="text-center">
              <div className="flex items-center justify-center gap-2 mb-2">
                <TrendingUp className="text-primary" size={32} />
                <span className="text-4xl font-bold text-text-primary">50K+</span>
              </div>
              <p className="text-text-secondary">月阅读量</p>
            </div>
          </div>
        </div>
      </section>

      {/* 精选文章 */}
      <section className="py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between mb-8">
            <h2 className="text-3xl font-bold text-text-primary">精选文章</h2>
            <Link href="/articles" className="text-primary hover:underline flex items-center gap-1">
              查看全部 →
            </Link>
          </div>

          {articles.length === 0 ? (
            <div className="text-center py-12 text-text-muted">
              <FileText size={48} className="mx-auto mb-4 opacity-50" />
              <p>暂无文章，快来创作第一篇吧！</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {articles.map((article: any) => (
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
                      <h3 className="text-lg font-semibold text-text-primary mb-2 line-clamp-2 group-hover:text-primary transition-colors">
                        {article.title}
                      </h3>
                      <p className="text-sm text-text-muted line-clamp-2 mb-3">
                        {article.content?.substring(0, 100).replace(/[#*`]/g, '')}...
                      </p>
                      <div className="flex items-center justify-between text-xs text-text-muted">
                        <span>{new Date(article.published_at || article.created_at).toLocaleDateString('zh-CN')}</span>
                        <span>{article.view_count || 0} 次阅读</span>
                      </div>
                    </div>
                  </article>
                </Link>
              ))}
            </div>
          )}
        </div>
      </section>

      {/* CTA 区域 */}
      <section className="py-16 bg-primary/10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-3xl font-bold text-text-primary mb-4">
            准备好开始创作了吗？
          </h2>
          <p className="text-lg text-text-secondary mb-8">
            使用 AI 技术快速生成高质量文章，加入我们的创作社区
          </p>
          <Link
            href="http://localhost:3000"
            className="inline-flex items-center gap-2 px-8 py-3 bg-primary text-white rounded-lg font-medium hover:bg-primary-dark transition-colors"
          >
            免费开始使用
          </Link>
        </div>
      </section>

      {/* 页脚 */}
      <footer className="bg-card border-t border-border py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col md:flex-row items-center justify-between">
            <p className="text-text-muted text-sm">
              © 2025 超能写手社区. All rights reserved.
            </p>
            <div className="flex items-center gap-6 mt-4 md:mt-0">
              <Link href="/articles" className="text-text-muted hover:text-primary text-sm">
                文章
              </Link>
              <Link href="/tags" className="text-text-muted hover:text-primary text-sm">
                标签
              </Link>
              <Link href="/search" className="text-text-muted hover:text-primary text-sm">
                搜索
              </Link>
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}
