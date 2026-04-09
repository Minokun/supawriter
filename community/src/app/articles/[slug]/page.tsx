import Link from 'next/link'
import { Calendar, Eye, Heart, MessageCircle, Share2, Tag, ArrowLeft } from 'lucide-react'
import { notFound } from 'next/navigation'
import ReactMarkdown from 'react-markdown'

interface Article {
  id: number
  user_id: number
  title: string
  slug: string
  content: string
  html_content: string
  cover_image: string | null
  status: string
  seo_title: string | null
  seo_desc: string | null
  tags: string[]
  view_count: number
  like_count: number
  comment_count: number
  created_at: string
  updated_at: string
  published_at: string
}

interface Props {
  params: {
    slug: string
  }
}

// 生成动态元数据
export async function generateMetadata({ params }: Props) {
  try {
    const res = await fetch(`http://localhost:8000/api/v1/articles/slug/${params.slug}`, {
      next: { revalidate: 60 }
    })

    if (!res.ok) {
      return {
        title: '文章未找到 - 超能写手社区',
      }
    }

    const article: Article = await res.json()

    return {
      title: article.seo_title || article.title,
      description: article.seo_desc || article.content?.substring(0, 160).replace(/[#*`]/g, ''),
      keywords: article.tags?.join(', ') || '',
      openGraph: {
        title: article.seo_title || article.title,
        description: article.seo_desc || article.content?.substring(0, 160).replace(/[#*`]/g, ''),
        type: 'article',
        publishedTime: article.published_at,
        authors: ['超能写手'],
        images: article.cover_image ? [article.cover_image] : [],
      },
      twitter: {
        card: 'summary_large_image',
        title: article.seo_title || article.title,
        description: article.seo_desc || article.content?.substring(0, 160).replace(/[#*`]/g, ''),
        images: article.cover_image ? [article.cover_image] : [],
      },
      alternates: {
        canonical: `http://localhost:3001/articles/${params.slug}`,
      }
    }
  } catch {
    return {
      title: '文章未找到 - 超能写手社区',
    }
  }
}

export default async function ArticlePage({ params }: Props) {
  try {
    const res = await fetch(`http://localhost:8000/api/v1/articles/slug/${params.slug}`, {
      next: { revalidate: 60 }
    })

    if (!res.ok) {
      notFound()
    }

    const article: Article = await res.json()

    // 增加浏览量（后台请求）
    fetch(`http://localhost:8000/api/v1/articles/${article.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ view_count: article.view_count + 1 }),
    }).catch(() => {})

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

        {/* 返回按钮 */}
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <Link
            href="/articles"
            className="inline-flex items-center gap-2 text-text-muted hover:text-primary transition-colors mb-6"
          >
            <ArrowLeft size={18} />
            返回文章列表
          </Link>
        </div>

        {/* 文章内容 */}
        <article className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 pb-16">
          {/* 封面图 */}
          {article.cover_image && (
            <div className="mb-8 rounded-xl overflow-hidden shadow-lg">
              <img
                src={article.cover_image}
                alt={article.title}
                className="w-full h-auto"
              />
            </div>
          )}

          {/* 标题 */}
          <h1 className="text-4xl md:text-5xl font-bold text-text-primary mb-4">
            {article.title}
          </h1>

          {/* 元信息 */}
          <div className="flex flex-wrap items-center gap-6 text-text-muted mb-8 pb-8 border-b border-border">
            <div className="flex items-center gap-2">
              <Calendar size={18} />
              <span>{new Date(article.published_at || article.created_at).toLocaleDateString('zh-CN')}</span>
            </div>
            <div className="flex items-center gap-2">
              <Eye size={18} />
              <span>{article.view_count || 0} 次阅读</span>
            </div>
            <div className="flex items-center gap-2">
              <Heart size={18} />
              <span>{article.like_count || 0} 次喜欢</span>
            </div>
            <div className="flex items-center gap-2">
              <MessageCircle size={18} />
              <span>{article.comment_count || 0} 条评论</span>
            </div>
          </div>

          {/* 标签 */}
          {article.tags && article.tags.length > 0 && (
            <div className="flex flex-wrap gap-2 mb-8">
              {article.tags.map((tag) => (
                <Link
                  key={tag}
                  href={`/tags/${tag}`}
                  className="inline-flex items-center gap-1 px-3 py-1 bg-primary/10 text-primary rounded-full text-sm hover:bg-primary/20 transition-colors"
                >
                  <Tag size={14} />
                  {tag}
                </Link>
              ))}
            </div>
          )}

          {/* 文章正文 */}
          <div className="prose prose-lg max-w-none">
            <ReactMarkdown>{article.content}</ReactMarkdown>
          </div>

          {/* 分享和操作 */}
          <div className="mt-12 pt-8 border-t border-border">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <button className="flex items-center gap-2 px-4 py-2 bg-card border border-border rounded-lg hover:border-primary transition-colors">
                  <Heart size={18} />
                  <span>喜欢</span>
                </button>
                <button className="flex items-center gap-2 px-4 py-2 bg-card border border-border rounded-lg hover:border-primary transition-colors">
                  <MessageCircle size={18} />
                  <span>评论</span>
                </button>
              </div>
              <button className="flex items-center gap-2 px-4 py-2 bg-card border border-border rounded-lg hover:border-primary transition-colors">
                <Share2 size={18} />
                <span>分享</span>
              </button>
            </div>
          </div>

          {/* 相关文章 */}
          <section className="mt-16 pt-8 border-t border-border">
            <h2 className="text-2xl font-bold text-text-primary mb-6">更多文章</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {[1, 2, 3].map((i) => (
                <div key={i} className="bg-card rounded-lg p-4 border border-border">
                  <div className="h-32 bg-background rounded mb-3"></div>
                  <h3 className="font-medium text-text-primary mb-2">相关文章标题</h3>
                  <p className="text-sm text-text-muted line-clamp-2">相关文章摘要内容...</p>
                </div>
              ))}
            </div>
          </section>
        </article>

        {/* 页脚 */}
        <footer className="bg-card border-t border-border py-8">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <p className="text-center text-text-muted text-sm">
              © 2025 超能写手社区. All rights reserved.
            </p>
          </div>
        </footer>
      </div>
    )
  }
} catch (error) {
  notFound()
}
}
