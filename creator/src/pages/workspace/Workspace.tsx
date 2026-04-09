import { Link } from 'react-router-dom'
import { PenTool, MessageSquare, Lightbulb, TrendingUp, FileText } from 'lucide-react'
import { useAuthStore } from '@store/authStore'

function Workspace() {
  const features = [
    {
      name: '超能写手',
      description: '使用 AI 技术快速生成高质量文章',
      icon: PenTool,
      color: 'bg-red-100 text-red-600',
      href: '/writer',
    },
    {
      name: 'AI 助手',
      description: '智能对话助手，帮助解决各种问题',
      icon: MessageSquare,
      color: 'bg-blue-100 text-blue-600',
      href: '/ai-chat',
    },
    {
      name: '文章再创作',
      description: '对现有文章进行优化和改写',
      icon: FileText,
      color: 'bg-green-100 text-green-600',
      href: '/rewrite',
    },
    {
      name: '灵感发现',
      description: '全网热点追踪，激发创作灵感',
      icon: Lightbulb,
      color: 'bg-yellow-100 text-yellow-600',
      href: '/inspiration',
    },
  ]

  return (
    <div className="space-y-8 fade-in">
      {/* 欢迎信息 */}
      <div>
        <h1 className="text-3xl font-bold text-text-primary mb-2">
          欢迎回来，{useAuthStore.getState().user?.display_name || '创作者'}！
        </h1>
        <p className="text-text-muted">
          选择一个功能开始创作吧
        </p>
      </div>

      {/* 功能卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {features.map((feature) => (
          <Link
            key={feature.name}
            to={feature.href}
            className="group"
          >
            <div className="bg-card rounded-xl p-6 shadow-md hover:shadow-lg transition-all hover:-translate-y-1">
              <div className="flex items-start gap-4">
                <div className={`p-3 rounded-lg ${feature.color}`}>
                  <feature.icon size={24} />
                </div>
                <div className="flex-1">
                  <h3 className="text-xl font-semibold text-text-primary mb-2 group-hover:text-primary transition-colors">
                    {feature.name}
                  </h3>
                  <p className="text-text-muted">{feature.description}</p>
                </div>
              </div>
            </div>
          </Link>
        ))}
      </div>

      {/* 热点预览 */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-2xl font-bold text-text-primary">灵感发现</h2>
          <Link
            to="/inspiration"
            className="text-primary hover:underline flex items-center gap-1"
          >
            查看全部 →
          </Link>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="bg-card rounded-lg p-4 border border-border hover:border-primary transition-colors">
              <div className="flex items-center gap-2 mb-2">
                <TrendingUp size={16} className="text-primary" />
                <span className="text-sm font-medium text-text-secondary">热点 {i}</span>
              </div>
              <p className="text-text-primary font-medium mb-2">热门话题标题占位符</p>
              <p className="text-sm text-text-muted line-clamp-2">
                这里是热点话题的简短描述...
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* 快捷操作 */}
      <div>
        <h2 className="text-2xl font-bold text-text-primary mb-4">快捷操作</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <button
            onClick={() => window.location.href = '/writer'}
            className="bg-cta text-white px-6 py-4 rounded-lg font-medium hover:bg-cta-dark transition-colors flex items-center justify-center gap-2"
          >
            <PenTool size={20} />
            <span>快速创作</span>
          </button>
          <button
            onClick={() => window.location.href = '/ai-chat'}
            className="bg-primary text-white px-6 py-4 rounded-lg font-medium hover:bg-primary-dark transition-colors flex items-center justify-center gap-2"
          >
            <MessageSquare size={20} />
            <span>打开 AI 助手</span>
          </button>
        </div>
      </div>
    </div>
  )
}

export default Workspace
