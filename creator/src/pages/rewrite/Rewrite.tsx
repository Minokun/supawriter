import { useState } from 'react'
import { FileText, Wand2, Copy, Check, Download, History, RefreshCw } from 'lucide-react'
import ReactMarkdown from 'react-markdown'

type RewriteStyle = 'professional' | 'casual' | 'creative' | 'academic' | 'concise'

function Rewrite() {
  const [originalText, setOriginalText] = useState('')
  const [rewrittenText, setRewrittenText] = useState('')
  const [selectedStyle, setSelectedStyle] = useState<RewriteStyle>('professional')
  const [isRewriting, setIsRewriting] = useState(false)
  const [copied, setCopied] = useState(false)
  const [history, setHistory] = useState<Array<{ original: string; rewritten: string; style: RewriteStyle; time: number }>>([])

  const styles = [
    { id: 'professional' as RewriteStyle, name: '专业', description: '正式、专业的语气', icon: '💼', color: 'bg-blue-100 text-blue-600' },
    { id: 'casual' as RewriteStyle, name: '轻松', description: '随意、亲切的语气', icon: '😊', color: 'bg-green-100 text-green-600' },
    { id: 'creative' as RewriteStyle, name: '创意', description: '新颖、有趣的风格', icon: '✨', color: 'bg-purple-100 text-purple-600' },
    { id: 'academic' as RewriteStyle, name: '学术', description: '严谨、学术化的表达', icon: '📚', color: 'bg-orange-100 text-orange-600' },
    { id: 'concise' as RewriteStyle, name: '简洁', description: '精简、直接的表达', icon: '📝', color: 'bg-gray-100 text-gray-600' },
  ]

  const handleRewrite = async () => {
    if (!originalText.trim()) {
      alert('请输入原文')
      return
    }

    setIsRewriting(true)

    try {
      // 调用后端 API 进行文章再创作
      const response = await fetch('/api/v1/articles/rewrite', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('supawriter-auth')?.match(/"token":"(.*?)"/)?.[1] || ''}`,
        },
        body: JSON.stringify({
          content: originalText,
          style: selectedStyle,
        }),
      })

      if (!response.ok) throw new Error('再创作失败')

      const data = await response.json()

      // 模拟结果（实际应该从后端获取）
      const mockResult = `${originalText}\n\n[再创作版本 - ${styles.find(s => s.id === selectedStyle)?.name}]\n\n这是一段经过${styles.find(s => s.id === selectedStyle)?.name}化处理的内容。AI 会根据您选择的风格，对原文进行改写，保持原意的同时调整语气和表达方式。`

      setRewrittenText(mockResult)

      // 添加到历史记录
      setHistory((prev) => [
        {
          original: originalText,
          rewritten: mockResult,
          style: selectedStyle,
          time: Date.now(),
        },
        ...prev,
      ])
    } catch (err) {
      console.error('Failed to rewrite:', err)
      alert('再创作失败，请重试')
    } finally {
      setIsRewriting(false)
    }
  }

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(rewrittenText)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (err) {
      console.error('Failed to copy:', err)
    }
  }

  const handleDownload = () => {
    const blob = new Blob([rewrittenText], { type: 'text/markdown' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `rewritten-${Date.now()}.md`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  const handleLoadFromHistory = (item: { original: string; rewritten: string; style: RewriteStyle }) => {
    setOriginalText(item.original)
    setRewrittenText(item.rewritten)
    setSelectedStyle(item.style)
  }

  const clearHistory = () => {
    if (confirm('确定要清空历史记录吗？')) {
      setHistory([])
    }
  }

  return (
    <div className="space-y-6">
      {/* 头部 */}
      <div>
        <h1 className="text-3xl font-bold text-text-primary flex items-center gap-2">
          <Wand2 className="text-primary" />
          文章再创作
        </h1>
        <p className="text-text-muted mt-1">使用 AI 对文章进行改写和优化</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 左侧：输入区域 */}
        <div className="space-y-4">
          {/* 原文输入 */}
          <div className="bg-card rounded-xl shadow-md p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-text-primary flex items-center gap-2">
                <FileText size={20} />
                原文
              </h2>
              <span className="text-sm text-text-muted">
                {originalText.length} 字符
              </span>
            </div>

            <textarea
              value={originalText}
              onChange={(e) => setOriginalText(e.target.value)}
              placeholder="请输入需要改写的文章内容..."
              rows={15}
              className="w-full px-4 py-3 rounded-lg border border-border focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent resize-none text-sm"
              disabled={isRewriting}
            />

            {/* 风格选择 */}
            <div className="mt-4">
              <label className="block text-sm font-medium text-text-primary mb-2">
                改写风格
              </label>
              <div className="grid grid-cols-3 md:grid-cols-5 gap-2">
                {styles.map((style) => (
                  <button
                    key={style.id}
                    onClick={() => setSelectedStyle(style.id)}
                    className={`p-2 rounded-lg border-2 transition-all text-center ${
                      selectedStyle === style.id
                        ? 'border-primary bg-primary/5'
                        : 'border-border hover:border-primary/50'
                    }`}
                    disabled={isRewriting}
                    title={style.description}
                  >
                    <div className={`p-1 rounded ${style.color} mb-1`}>
                      <span className="text-sm">{style.icon}</span>
                    </div>
                    <p className="text-xs font-medium text-text-primary">{style.name}</p>
                  </button>
                ))}
              </div>
            </div>

            {/* 改写按钮 */}
            <button
              onClick={handleRewrite}
              disabled={!originalText.trim() || isRewriting}
              className="w-full mt-4 bg-primary text-white py-3 rounded-lg font-medium hover:bg-primary-dark transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              <Wand2 size={18} className={isRewriting ? 'animate-pulse' : ''} />
              <span>{isRewriting ? '改写中...' : '开始改写'}</span>
            </button>
          </div>

          {/* 历史记录 */}
          {history.length > 0 && (
            <div className="bg-card rounded-xl shadow-md p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-text-primary flex items-center gap-2">
                  <History size={18} />
                  历史记录
                </h3>
                <button
                  onClick={clearHistory}
                  className="text-sm text-text-muted hover:text-red-500 transition-colors"
                >
                  清空
                </button>
              </div>

              <div className="space-y-2 max-h-64 overflow-y-auto">
                {history.map((item, index) => (
                  <button
                    key={index}
                    onClick={() => handleLoadFromHistory(item)}
                    className="w-full p-3 bg-background rounded-lg hover:border-primary border border-transparent text-left transition-colors"
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm font-medium text-text-primary line-clamp-1">
                        {item.original.substring(0, 50)}...
                      </span>
                      <span className="text-xs px-2 py-0.5 bg-primary/10 text-primary rounded-full">
                        {styles.find((s) => s.id === item.style)?.name}
                      </span>
                    </div>
                    <p className="text-xs text-text-muted">
                      {new Date(item.time).toLocaleString('zh-CN')}
                    </p>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* 右侧：结果区域 */}
        <div>
          <div className="bg-card rounded-xl shadow-md p-6 sticky top-4">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-text-primary flex items-center gap-2">
                <RefreshCw size={20} />
                改写结果
              </h2>

              {rewrittenText && (
                <div className="flex gap-2">
                  <button
                    onClick={handleCopy}
                    className="p-2 text-text-muted hover:text-primary hover:bg-primary/10 rounded-lg transition-colors"
                    title="复制"
                  >
                    {copied ? <Check size={18} className="text-green-500" /> : <Copy size={18} />}
                  </button>

                  <button
                    onClick={handleDownload}
                    className="p-2 text-text-muted hover:text-primary hover:bg-primary/10 rounded-lg transition-colors"
                    title="下载"
                  >
                    <Download size={18} />
                  </button>
                </div>
              )}
            </div>

            {isRewriting ? (
              <div className="flex items-center justify-center py-20">
                <div className="text-center">
                  <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4" />
                  <p className="text-text-muted">AI 正在改写中...</p>
                </div>
              </div>
            ) : rewrittenText ? (
              <div className="prose prose-sm max-w-none max-h-[600px] overflow-y-auto">
                <ReactMarkdown>{rewrittenText}</ReactMarkdown>
              </div>
            ) : (
              <div className="flex items-center justify-center py-20 text-center">
                <div>
                  <Wand2 size={48} className="text-text-muted mx-auto mb-4" />
                  <p className="text-text-muted">输入原文并选择风格后</p>
                  <p className="text-text-muted">点击"开始改写"查看结果</p>
                </div>
              </div>
            )}

            {/* 操作提示 */}
            {rewrittenText && !isRewriting && (
              <div className="mt-4 pt-4 border-t border-border">
                <p className="text-xs text-text-muted text-center">
                  您可以复制结果或下载为 Markdown 文件
                </p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 使用提示 */}
      <div className="bg-primary/5 rounded-xl p-6 border border-primary/20">
        <h3 className="text-lg font-semibold text-text-primary mb-3 flex items-center gap-2">
          <Wand2 size={20} className="text-primary" />
          使用提示
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm text-text-secondary">
          <div>
            <h4 className="font-medium text-text-primary mb-2">适用场景</h4>
            <ul className="space-y-1">
              <li>• 优化文章表达方式</li>
              <li>• 调整内容语气风格</li>
              <li>• 简化或扩展内容</li>
              <li>• 改写避免重复</li>
            </ul>
          </div>
          <div>
            <h4 className="font-medium text-text-primary mb-2">注意事项</h4>
            <ul className="space-y-1">
              <li>• AI 改写会保持原意</li>
              <li>• 建议人工检查结果</li>
              <li>• 可以多次尝试不同风格</li>
              <li>• 历史记录帮助对比效果</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Rewrite
