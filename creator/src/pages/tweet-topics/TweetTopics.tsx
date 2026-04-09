import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Twitter,
  Sparkles,
  Hash,
  Copy,
  Check,
  Trash2,
  RefreshCw,
  TrendingUp,
  History,
} from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import { zhCN } from 'date-fns/locale'
import { tweetTopicsAPI } from '@lib/api'

interface TopicDetail {
  title: string
  subtitle?: string
  angle?: string
  target_audience?: string
  seo_keywords?: string[]
  tags?: string[]
  content_outline?: Array<{ h1?: string; h2?: string[] } | string>
  hook?: string
  value_proposition?: string
  interaction_point?: string
  share_trigger?: string
  estimated_words?: string
  difficulty?: string
  heat_score?: number
}

interface TopicsData {
  topics: TopicDetail[]
  summary?: string
  hot_keywords?: string[]
}

interface HistoryRecord {
  id: number
  news_source: string
  news_count: number
  topics_data: TopicsData
  model_type?: string
  model_name?: string
  timestamp: string
}

const newsSources = [
  { id: '澎湃科技', name: '澎湃科技', desc: '科技热点聚焦' },
  { id: 'SOTA开源项目', name: 'SOTA开源项目', desc: '前沿开源项目' },
  { id: '实时新闻', name: '实时新闻', desc: '即时行业动态' },
]

function TweetTopics() {
  const navigate = useNavigate()

  const [activeTab, setActiveTab] = useState<'generate' | 'history'>('generate')
  const [newsSource, setNewsSource] = useState<string>('澎湃科技')
  const [newsCount, setNewsCount] = useState(15)
  const [topicCount, setTopicCount] = useState(8)
  const [isGenerating, setIsGenerating] = useState(false)
  const [generatedRecord, setGeneratedRecord] = useState<HistoryRecord | null>(null)
  const [history, setHistory] = useState<HistoryRecord[]>([])
  const [isLoadingHistory, setIsLoadingHistory] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [copiedId, setCopiedId] = useState<string | null>(null)

  const loadHistory = async () => {
    try {
      setIsLoadingHistory(true)
      const data = await tweetTopicsAPI.history()
      setHistory(data || [])
    } catch (err) {
      console.error('Failed to load tweet topics history:', err)
      setError('加载历史记录失败，请稍后重试')
    } finally {
      setIsLoadingHistory(false)
    }
  }

  useEffect(() => {
    if (activeTab === 'history') {
      loadHistory()
    }
  }, [activeTab])

  const handleGenerate = async () => {
    setError(null)
    setIsGenerating(true)

    try {
      const result = await tweetTopicsAPI.generate({
        news_source: newsSource,
        news_count: newsCount,
        topic_count: topicCount,
      })

      if (result?.record) {
        setGeneratedRecord(result.record)
      } else {
        setError('生成失败，未获取到有效结果')
      }
    } catch (err) {
      console.error('Failed to generate topics:', err)
      setError('生成失败，请重试')
    } finally {
      setIsGenerating(false)
    }
  }

  const handleCopy = async (content: string, id: string) => {
    try {
      await navigator.clipboard.writeText(content)
      setCopiedId(id)
      setTimeout(() => setCopiedId(null), 2000)
    } catch (err) {
      console.error('Failed to copy:', err)
    }
  }

  const handleDeleteRecord = async (recordId: number) => {
    if (!confirm('确定要删除该记录吗？')) return

    try {
      await tweetTopicsAPI.delete(recordId)
      setHistory((prev) => prev.filter((item) => item.id !== recordId))
    } catch (err) {
      console.error('Failed to delete record:', err)
      setError('删除失败，请重试')
    }
  }

  const buildStylePrompt = (topic: TopicDetail) => {
    const parts = []
    if (topic.angle) parts.push(`切入角度：${topic.angle}`)
    if (topic.target_audience) parts.push(`目标读者：${topic.target_audience}`)
    if (topic.hook) parts.push(`开篇钩子：${topic.hook}`)
    if (topic.value_proposition) parts.push(`价值主张：${topic.value_proposition}`)
    if (topic.interaction_point) parts.push(`互动引导：${topic.interaction_point}`)
    if (topic.share_trigger) parts.push(`分享触发点：${topic.share_trigger}`)
    return parts.join('\n')
  }

  const handleGenerateArticle = (topic: TopicDetail) => {
    navigate('/writer', {
      state: {
        topic: topic.title,
        customStyle: buildStylePrompt(topic),
        articleType: 'social_media',
      },
    })
  }

  const renderOutline = (outline?: TopicDetail['content_outline']) => {
    if (!outline || outline.length === 0) return null

    return (
      <div className="space-y-2">
        {outline.map((section, index) => {
          if (typeof section === 'string') {
            return (
              <div key={index} className="text-sm text-text-secondary">
                {index + 1}. {section}
              </div>
            )
          }

          const h1 = section.h1 || `段落 ${index + 1}`
          const h2List = section.h2 || []

          return (
            <div key={index} className="text-sm text-text-secondary">
              <div className="font-medium text-text-primary">{index + 1}. {h1}</div>
              {h2List.length > 0 && (
                <div className="mt-1 space-y-1">
                  {h2List.map((h2, h2Index) => (
                    <div key={h2Index} className="text-text-muted">
                      - {h2}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )
        })}
      </div>
    )
  }

  const renderTopics = (topics: TopicDetail[]) => (
    <div className="space-y-4">
      {topics.map((topic, index) => (
        <div
          key={`${topic.title}-${index}`}
          className="p-4 bg-background rounded-lg border border-border hover:border-primary/30 transition-colors"
        >
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-3 flex-wrap">
                <span className="text-xs font-semibold text-primary">#{index + 1}</span>
                <h3 className="text-text-primary font-semibold text-lg">{topic.title}</h3>
                {typeof topic.heat_score === 'number' && (
                  <span className="text-xs px-2 py-1 rounded-full bg-orange-100 text-orange-700">
                    热度 {topic.heat_score}/10
                  </span>
                )}
              </div>

              {topic.subtitle && (
                <p className="text-sm text-text-muted mt-1">{topic.subtitle}</p>
              )}

              <div className="flex flex-wrap gap-2 mt-3">
                {topic.angle && (
                  <span className="text-xs px-2 py-1 bg-primary/10 text-primary rounded-full">
                    角度：{topic.angle}
                  </span>
                )}
                {topic.target_audience && (
                  <span className="text-xs px-2 py-1 bg-green-100 text-green-700 rounded-full">
                    受众：{topic.target_audience}
                  </span>
                )}
                {topic.difficulty && (
                  <span className="text-xs px-2 py-1 bg-blue-100 text-blue-700 rounded-full">
                    难度：{topic.difficulty}
                  </span>
                )}
                {topic.estimated_words && (
                  <span className="text-xs px-2 py-1 bg-purple-100 text-purple-700 rounded-full">
                    字数：{topic.estimated_words}
                  </span>
                )}
              </div>

              {topic.tags && topic.tags.length > 0 && (
                <div className="flex flex-wrap gap-2 mt-3">
                  {topic.tags.map((tag, tagIndex) => (
                    <span
                      key={`${tag}-${tagIndex}`}
                      className="text-xs px-2 py-1 bg-primary/5 text-primary rounded-full"
                    >
                      <Hash size={10} className="inline mr-1" />
                      {tag}
                    </span>
                  ))}
                </div>
              )}

              {topic.seo_keywords && topic.seo_keywords.length > 0 && (
                <div className="flex flex-wrap gap-2 mt-2">
                  {topic.seo_keywords.map((keyword, keywordIndex) => (
                    <span
                      key={`${keyword}-${keywordIndex}`}
                      className="text-xs px-2 py-1 bg-gray-100 text-text-secondary rounded-full"
                    >
                      #{keyword}
                    </span>
                  ))}
                </div>
              )}

              <details className="mt-3">
                <summary className="text-sm text-primary cursor-pointer">查看详情</summary>
                <div className="mt-3 space-y-3">
                  {topic.hook && (
                    <div>
                      <div className="text-xs text-text-muted">开篇钩子</div>
                      <div className="text-sm text-text-primary">{topic.hook}</div>
                    </div>
                  )}
                  {topic.value_proposition && (
                    <div>
                      <div className="text-xs text-text-muted">价值主张</div>
                      <div className="text-sm text-text-primary">{topic.value_proposition}</div>
                    </div>
                  )}
                  {topic.interaction_point && (
                    <div>
                      <div className="text-xs text-text-muted">互动引导</div>
                      <div className="text-sm text-text-primary">{topic.interaction_point}</div>
                    </div>
                  )}
                  {topic.share_trigger && (
                    <div>
                      <div className="text-xs text-text-muted">分享触发点</div>
                      <div className="text-sm text-text-primary">{topic.share_trigger}</div>
                    </div>
                  )}
                  {renderOutline(topic.content_outline)}
                </div>
              </details>
            </div>

            <div className="flex items-center gap-1">
              <button
                onClick={() => handleCopy(topic.title, `topic-${index}`)}
                className="p-2 text-text-muted hover:text-primary hover:bg-primary/10 rounded-lg transition-colors"
                title="复制标题"
              >
                {copiedId === `topic-${index}` ? (
                  <Check size={16} className="text-green-500" />
                ) : (
                  <Copy size={16} />
                )}
              </button>
            </div>
          </div>

          <div className="mt-4 flex flex-wrap gap-3">
            <button
              onClick={() => handleGenerateArticle(topic)}
              className="px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary-dark transition-colors text-sm font-medium"
            >
              生成文章
            </button>
            <button
              onClick={() => handleCopy(JSON.stringify(topic, null, 2), `detail-${index}`)}
              className="px-4 py-2 bg-card border border-border rounded-lg hover:border-primary transition-colors text-sm font-medium"
            >
              复制详情
            </button>
          </div>
        </div>
      ))}
    </div>
  )

  const currentTopics = generatedRecord?.topics_data?.topics || []

  return (
    <div className="space-y-6">
      {/* 头部 */}
      <div>
        <h1 className="text-3xl font-bold text-text-primary flex items-center gap-2">
          <Twitter className="text-primary" />
          推文选题
        </h1>
        <p className="text-text-muted mt-1">AI 驱动的社交媒体内容选题生成器</p>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-2">
        <button
          onClick={() => setActiveTab('generate')}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            activeTab === 'generate'
              ? 'bg-primary text-white'
              : 'bg-card border border-border text-text-secondary hover:text-primary'
          }`}
        >
          生成选题
        </button>
        <button
          onClick={() => setActiveTab('history')}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-1 ${
            activeTab === 'history'
              ? 'bg-primary text-white'
              : 'bg-card border border-border text-text-secondary hover:text-primary'
          }`}
        >
          <History size={14} />
          历史记录
        </button>
      </div>

      {/* 错误提示 */}
      {error && (
        <div className="p-4 bg-red-50 border border-red-200 text-red-600 rounded-lg">
          {error}
        </div>
      )}

      {activeTab === 'generate' && (
        <div className="space-y-6">
          {/* 生成表单 */}
          <div className="bg-card rounded-xl shadow-md p-6 space-y-6">
            <div>
              <h2 className="text-xl font-semibold text-text-primary mb-2">生成选题</h2>
              <p className="text-sm text-text-muted">选择新闻源与数量，生成高质量推文选题</p>
            </div>

            <div>
              <label className="block text-sm font-medium text-text-primary mb-3">
                新闻源
              </label>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                {newsSources.map((source) => (
                  <button
                    key={source.id}
                    onClick={() => setNewsSource(source.id)}
                    className={`p-4 rounded-lg border-2 text-left transition-all ${
                      newsSource === source.id
                        ? 'border-primary bg-primary/5'
                        : 'border-border hover:border-primary/50'
                    }`}
                    disabled={isGenerating}
                  >
                    <div className="font-medium text-text-primary">{source.name}</div>
                    <div className="text-xs text-text-muted mt-1">{source.desc}</div>
                  </button>
                ))}
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="block text-sm font-medium text-text-primary mb-2">
                  新闻数量
                </label>
                <input
                  type="range"
                  min={5}
                  max={30}
                  step={5}
                  value={newsCount}
                  onChange={(e) => setNewsCount(Number(e.target.value))}
                  disabled={isGenerating}
                  className="w-full"
                />
                <div className="text-xs text-text-muted mt-1">当前：{newsCount} 条</div>
              </div>

              <div>
                <label className="block text-sm font-medium text-text-primary mb-2">
                  选题数量
                </label>
                <input
                  type="range"
                  min={3}
                  max={15}
                  step={1}
                  value={topicCount}
                  onChange={(e) => setTopicCount(Number(e.target.value))}
                  disabled={isGenerating}
                  className="w-full"
                />
                <div className="text-xs text-text-muted mt-1">当前：{topicCount} 个</div>
              </div>
            </div>

            <button
              onClick={handleGenerate}
              disabled={isGenerating}
              className="w-full bg-primary text-white py-4 rounded-lg font-medium hover:bg-primary-dark transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              <Sparkles size={20} className={isGenerating ? 'animate-pulse' : ''} />
              <span>{isGenerating ? '生成中...' : '生成选题'}</span>
            </button>
          </div>

          {/* 生成结果 */}
          {generatedRecord && (
            <div className="bg-card rounded-xl shadow-md p-6 space-y-4">
              <div className="flex items-center justify-between flex-wrap gap-2">
                <div>
                  <h2 className="text-xl font-semibold text-text-primary">生成结果</h2>
                  <p className="text-xs text-text-muted mt-1">
                    来源：{generatedRecord.news_source} · 新闻 {generatedRecord.news_count} 条 · {currentTopics.length} 个选题
                  </p>
                </div>
                <button
                  onClick={() => handleCopy(currentTopics.map((t) => t.title).join('\n'), 'all')}
                  className="px-3 py-2 text-sm bg-card border border-border rounded-lg hover:border-primary transition-colors"
                >
                  复制全部标题
                </button>
              </div>

              {generatedRecord.topics_data?.summary && (
                <div className="bg-primary/5 border border-primary/20 rounded-lg p-4 text-sm text-text-secondary">
                  {generatedRecord.topics_data.summary}
                </div>
              )}

              {generatedRecord.topics_data?.hot_keywords && generatedRecord.topics_data.hot_keywords.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {generatedRecord.topics_data.hot_keywords.map((keyword, index) => (
                    <span
                      key={`${keyword}-${index}`}
                      className="text-xs px-2 py-1 bg-primary/10 text-primary rounded-full"
                    >
                      #{keyword}
                    </span>
                  ))}
                </div>
              )}

              {currentTopics.length > 0 ? (
                renderTopics(currentTopics)
              ) : (
                <div className="text-center text-text-muted py-10">暂无选题结果</div>
              )}

              {currentTopics.length > 0 && (
                <div className="pt-4 border-t border-border flex flex-wrap gap-3">
                  <button
                    onClick={() => {
                      const randomTopic = currentTopics[Math.floor(Math.random() * currentTopics.length)]
                      handleCopy(randomTopic.title, 'random')
                    }}
                    className="px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary-dark transition-colors text-sm font-medium flex items-center gap-2"
                  >
                    <TrendingUp size={16} />
                    随机复制一个
                  </button>
                </div>
              )}
            </div>
          )}

          {!generatedRecord && (
            <div className="bg-card rounded-xl shadow-md p-12 text-center">
              <Twitter size={48} className="text-text-muted mx-auto mb-4" />
              <p className="text-text-muted">选择新闻源并生成你的第一组推文选题</p>
            </div>
          )}
        </div>
      )}

      {activeTab === 'history' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-semibold text-text-primary">历史记录</h2>
            <button
              onClick={loadHistory}
              disabled={isLoadingHistory}
              className="flex items-center gap-2 px-4 py-2 bg-card border border-border rounded-lg hover:border-primary transition-colors disabled:opacity-50"
            >
              <RefreshCw size={16} className={isLoadingHistory ? 'animate-spin' : ''} />
              刷新
            </button>
          </div>

          {isLoadingHistory && history.length === 0 ? (
            <div className="bg-card rounded-xl shadow-md p-12 text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4" />
              <p className="text-text-muted">加载中...</p>
            </div>
          ) : history.length === 0 ? (
            <div className="bg-card rounded-xl shadow-md p-12 text-center">
              <History size={48} className="text-text-muted mx-auto mb-4" />
              <p className="text-text-muted">暂无历史记录</p>
            </div>
          ) : (
            <div className="space-y-4">
              {history.map((record) => (
                <div key={record.id} className="bg-card rounded-xl shadow-md p-6 space-y-4">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <h3 className="text-lg font-semibold text-text-primary">
                        {record.news_source}
                      </h3>
                      <p className="text-xs text-text-muted mt-1">
                        {formatDistanceToNow(new Date(record.timestamp), { addSuffix: true, locale: zhCN })}
                        {' · '}新闻 {record.news_count} 条 · {record.topics_data?.topics?.length || 0} 个选题
                      </p>
                    </div>
                    <button
                      onClick={() => handleDeleteRecord(record.id)}
                      className="p-2 text-text-muted hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
                      title="删除"
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>

                  {record.topics_data?.summary && (
                    <div className="bg-primary/5 border border-primary/20 rounded-lg p-4 text-sm text-text-secondary">
                      {record.topics_data.summary}
                    </div>
                  )}

                  {record.topics_data?.hot_keywords && record.topics_data.hot_keywords.length > 0 && (
                    <div className="flex flex-wrap gap-2">
                      {record.topics_data.hot_keywords.map((keyword, index) => (
                        <span
                          key={`${keyword}-${index}`}
                          className="text-xs px-2 py-1 bg-primary/10 text-primary rounded-full"
                        >
                          #{keyword}
                        </span>
                      ))}
                    </div>
                  )}

                  {record.topics_data?.topics && record.topics_data.topics.length > 0 ? (
                    renderTopics(record.topics_data.topics)
                  ) : (
                    <div className="text-sm text-text-muted">该记录没有选题数据</div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default TweetTopics
