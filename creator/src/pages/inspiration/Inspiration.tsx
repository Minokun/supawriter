import { useEffect, useState } from 'react'
import { TrendingUp, ExternalLink, RefreshCw, Filter } from 'lucide-react'
import { hotspotAPI } from '@lib/api'

interface Hotspot {
  id: string
  title: string
  description: string
  url: string
  source: string
  rank: number
  heat: number
  created_at: string
}

interface SourceInfo {
  id: string
  name: string
  description: string
  icon: string
}

const sources: SourceInfo[] = [
  { id: 'weibo', name: '微博热搜', description: '微博平台热门话题', icon: '🔥' },
  { id: 'zhihu', name: '知乎热榜', description: '知乎平台热门问题', icon: '💡' },
  { id: 'douyin', name: '抖音热点', description: '抖音平台热门视频', icon: '🎵' },
  { id: 'baidu', name: '百度热搜', description: '百度搜索热门词', icon: '🔍' },
  { id: 'toutiao', name: '今日头条', description: '今日头条热门资讯', icon: '📰' },
]

function Inspiration() {
  const [hotspots, setHotspots] = useState<Hotspot[]>([])
  const [selectedSource, setSelectedSource] = useState<string>('all')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const loadHotspots = async () => {
    try {
      setIsLoading(true)
      setError(null)

      const params = selectedSource !== 'all' ? { source: selectedSource } : {}
      const data = await hotspotAPI.getAll(params)

      setHotspots(data || [])
    } catch (err) {
      console.error('Failed to load hotspots:', err)
      setError('加载热点失败，请稍后重试')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    loadHotspots()
  }, [selectedSource])

  const getSourceName = (sourceId: string) => {
    const source = sources.find((s) => s.id === sourceId)
    return source?.name || sourceId
  }

  const getHeatColor = (heat: number) => {
    if (heat >= 1000000) return 'text-red-600'
    if (heat >= 500000) return 'text-orange-500'
    if (heat >= 100000) return 'text-yellow-500'
    return 'text-text-muted'
  }

  const formatHeat = (heat: number) => {
    if (heat >= 1000000) return `${(heat / 1000000).toFixed(1)}M`
    if (heat >= 1000) return `${(heat / 1000).toFixed(1)}K`
    return heat.toString()
  }

  return (
    <div className="space-y-6">
      {/* 头部 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-text-primary">灵感发现</h1>
          <p className="text-text-muted mt-1">追踪全网热点，激发创作灵感</p>
        </div>

        <button
          onClick={loadHotspots}
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

      {/* 来源筛选 */}
      <div className="bg-card rounded-xl shadow-md p-6">
        <div className="flex items-center gap-3 mb-4">
          <Filter size={20} className="text-text-muted" />
          <h3 className="text-lg font-semibold text-text-primary">选择来源</h3>
        </div>

        <div className="flex flex-wrap gap-3">
          <button
            onClick={() => setSelectedSource('all')}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              selectedSource === 'all'
                ? 'bg-primary text-white'
                : 'bg-background text-text-secondary hover:text-primary'
            }`}
          >
            全部
          </button>

          {sources.map((source) => (
            <button
              key={source.id}
              onClick={() => setSelectedSource(source.id)}
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                selectedSource === source.id
                  ? 'bg-primary text-white'
                  : 'bg-background text-text-secondary hover:text-primary'
              }`}
            >
              <span className="mr-1">{source.icon}</span>
              {source.name}
            </button>
          ))}
        </div>
      </div>

      {/* 热点列表 */}
      {isLoading && hotspots.length === 0 ? (
        <div className="bg-card rounded-xl shadow-md p-12 text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4" />
          <p className="text-text-muted">加载中...</p>
        </div>
      ) : hotspots.length === 0 ? (
        <div className="bg-card rounded-xl shadow-md p-12 text-center">
          <TrendingUp size={48} className="text-text-muted mx-auto mb-4" />
          <p className="text-text-muted">暂无热点数据</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {hotspots.map((hotspot, index) => (
            <div
              key={hotspot.id}
              className="bg-card rounded-xl shadow-md p-5 hover:shadow-lg transition-all hover:-translate-y-1 group"
            >
              {/* 排名 */}
              <div className="flex items-start justify-between mb-3">
                <div
                  className={`flex items-center justify-center w-8 h-8 rounded-full font-bold text-sm ${
                    index < 3
                      ? 'bg-gradient-to-r from-red-500 to-orange-500 text-white'
                      : 'bg-background text-text-muted'
                  }`}
                >
                  {hotspot.rank || index + 1}
                </div>

                <div className={`flex items-center gap-1 ${getHeatColor(hotspot.heat)}`}>
                  <TrendingUp size={14} />
                  <span className="text-sm font-medium">{formatHeat(hotspot.heat)}</span>
                </div>
              </div>

              {/* 标题 */}
              <h3 className="text-lg font-semibold text-text-primary mb-2 line-clamp-2 group-hover:text-primary transition-colors">
                {hotspot.title}
              </h3>

              {/* 描述 */}
              {hotspot.description && (
                <p className="text-sm text-text-muted line-clamp-2 mb-3">
                  {hotspot.description}
                </p>
              )}

              {/* 来源标签 */}
              <div className="flex items-center justify-between">
                <span className="text-xs px-2 py-1 bg-background rounded-full text-text-secondary">
                  {getSourceName(hotspot.source)}
                </span>

                {hotspot.url && (
                  <a
                    href={hotspot.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="p-1.5 text-text-muted hover:text-primary hover:bg-primary/10 rounded-lg transition-colors"
                    title="查看原文"
                  >
                    <ExternalLink size={16} />
                  </a>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* 来源说明 */}
      <div className="bg-card rounded-xl shadow-md p-6">
        <h3 className="text-lg font-semibold text-text-primary mb-4">数据来源说明</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {sources.map((source) => (
            <div key={source.id} className="flex items-start gap-3 p-3 bg-background rounded-lg">
              <span className="text-2xl">{source.icon}</span>
              <div>
                <h4 className="font-medium text-text-primary">{source.name}</h4>
                <p className="text-sm text-text-muted">{source.description}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

export default Inspiration
