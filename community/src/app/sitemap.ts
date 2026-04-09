import { MetadataRoute } from 'next'

export default function sitemap(): MetadataRoute.Sitemap {
  const baseUrl = 'http://localhost:3001'

  // 静态页面
  const staticPages = [
    {
      url: baseUrl,
      lastModified: new Date(),
      changeFrequency: 'daily' as const,
      priority: 1,
    },
    {
      url: `${baseUrl}/articles`,
      lastModified: new Date(),
      changeFrequency: 'hourly' as const,
      priority: 0.9,
    },
    {
      url: `${baseUrl}/tags`,
      lastModified: new Date(),
      changeFrequency: 'daily' as const,
      priority: 0.8,
    },
    {
      url: `${baseUrl}/search`,
      lastModified: new Date(),
      changeFrequency: 'monthly' as const,
      priority: 0.5,
    },
  ]

  // 获取所有已发布的文章
  let articles: any[] = []
  try {
    const res = await fetch('http://localhost:8000/api/v1/articles?status=published&page_size=1000')
    if (res.ok) {
      articles = await res.json()
    }
  } catch (error) {
    console.error('Failed to fetch articles for sitemap:', error)
  }

  // 文章页面
  const articlePages = articles.map((article) => ({
    url: `${baseUrl}/articles/${article.slug || article.id}`,
    lastModified: new Date(article.updated_at || article.published_at),
    changeFrequency: 'weekly' as const,
    priority: 0.7,
  }))

  return [...staticPages, ...articlePages]
}
