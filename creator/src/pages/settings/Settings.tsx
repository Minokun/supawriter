import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '@store/authStore'
import {
  User,
  Bell,
  Lock,
  Palette,
  Globe,
  CreditCard,
  HelpCircle,
  LogOut,
  Save,
  Eye,
  EyeOff,
} from 'lucide-react'

interface SettingsData {
  // 个人信息
  displayName: string
  email: string
  avatar: string

  // 通知设置
  emailNotifications: boolean
  pushNotifications: boolean
  taskUpdates: boolean
  weeklyReport: boolean

  // 偏好设置
  language: 'zh-CN' | 'en-US'
  theme: 'light' | 'dark' | 'auto'
  defaultArticleType: string
  autoSave: boolean

  // API 设置
  apiKey: string
  apiEndpoint: string
}

function Settings() {
  const navigate = useNavigate()
  const { user, logout, updateProfile } = useAuthStore()

  const [settings, setSettings] = useState<SettingsData>({
    displayName: user?.display_name || '',
    email: user?.email || '',
    avatar: user?.avatar || '',

    emailNotifications: true,
    pushNotifications: false,
    taskUpdates: true,
    weeklyReport: true,

    language: 'zh-CN',
    theme: 'light',
    defaultArticleType: 'blog',
    autoSave: true,

    apiKey: '',
    apiEndpoint: 'https://api.openai.com/v1',
  })

  const [showApiKey, setShowApiKey] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [saveMessage, setSaveMessage] = useState('')

  const handleSave = async () => {
    setIsSaving(true)
    setSaveMessage('')

    try {
      // 这里调用 API 保存设置
      const response = await fetch('/api/v1/settings', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('supawriter-auth')?.match(/"token":"(.*?)"/)?.[1] || ''}`,
        },
        body: JSON.stringify(settings),
      })

      if (!response.ok) throw new Error('保存失败')

      setSaveMessage('设置已保存')
      setTimeout(() => setSaveMessage(''), 3000)
    } catch (err) {
      console.error('Failed to save settings:', err)
      setSaveMessage('保存失败，请重试')
    } finally {
      setIsSaving(false)
    }
  }

  const handleLogout = async () => {
    if (confirm('确定要退出登录吗？')) {
      await logout()
      navigate('/auth/login')
    }
  }

  const sections = [
    {
      id: 'profile',
      title: '个人信息',
      icon: User,
      color: 'text-blue-500',
    },
    {
      id: 'notifications',
      title: '通知设置',
      icon: Bell,
      color: 'text-green-500',
    },
    {
      id: 'preferences',
      title: '偏好设置',
      icon: Palette,
      color: 'text-purple-500',
    },
    {
      id: 'security',
      title: '安全设置',
      icon: Lock,
      color: 'text-red-500',
    },
    {
      id: 'api',
      title: 'API 设置',
      icon: Globe,
      color: 'text-orange-500',
    },
  ]

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* 头部 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-text-primary">系统设置</h1>
          <p className="text-text-muted mt-1">管理您的账户和偏好设置</p>
        </div>

        <button
          onClick={handleLogout}
          className="flex items-center gap-2 px-4 py-2 text-text-muted hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
        >
          <LogOut size={18} />
          <span>退出登录</span>
        </button>
      </div>

      {/* 保存消息 */}
      {saveMessage && (
        <div
          className={`p-4 rounded-lg ${
            saveMessage === '设置已保存'
              ? 'bg-green-50 border border-green-200 text-green-600'
              : 'bg-red-50 border border-red-200 text-red-600'
          }`}
        >
          {saveMessage}
        </div>
      )}

      {/* 个人信息 */}
      <div className="bg-card rounded-xl shadow-md p-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="p-2 bg-blue-100 rounded-lg">
            <User size={24} className="text-blue-500" />
          </div>
          <div>
            <h2 className="text-xl font-semibold text-text-primary">个人信息</h2>
            <p className="text-sm text-text-muted">更新您的个人资料</p>
          </div>
        </div>

        <div className="space-y-4">
          {/* 头像 */}
          <div className="flex items-center gap-4">
            {settings.avatar || user?.avatar ? (
              <img
                src={settings.avatar || user?.avatar}
                alt="Avatar"
                className="w-20 h-20 rounded-full object-cover"
              />
            ) : (
              <div className="w-20 h-20 rounded-full bg-primary text-white flex items-center justify-center text-2xl font-medium">
                {(settings.displayName || user?.display_name || user?.username || 'U').charAt(0).toUpperCase()}
              </div>
            )}
            <div>
              <button className="px-4 py-2 bg-primary text-white rounded-lg text-sm hover:bg-primary-dark transition-colors">
                更换头像
              </button>
              <p className="text-xs text-text-muted mt-1">支持 JPG、PNG 格式，最大 2MB</p>
            </div>
          </div>

          {/* 显示名称 */}
          <div>
            <label className="block text-sm font-medium text-text-primary mb-2">
              显示名称
            </label>
            <input
              type="text"
              value={settings.displayName}
              onChange={(e) => setSettings({ ...settings, displayName: e.target.value })}
              className="w-full px-4 py-2 rounded-lg border border-border focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
            />
          </div>

          {/* 邮箱 */}
          <div>
            <label className="block text-sm font-medium text-text-primary mb-2">
              邮箱地址
            </label>
            <input
              type="email"
              value={settings.email}
              disabled
              className="w-full px-4 py-2 rounded-lg border border-border bg-background text-text-muted"
            />
            <p className="text-xs text-text-muted mt-1">邮箱地址不可修改</p>
          </div>
        </div>
      </div>

      {/* 通知设置 */}
      <div className="bg-card rounded-xl shadow-md p-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="p-2 bg-green-100 rounded-lg">
            <Bell size={24} className="text-green-500" />
          </div>
          <div>
            <h2 className="text-xl font-semibold text-text-primary">通知设置</h2>
            <p className="text-sm text-text-muted">选择您希望接收的通知</p>
          </div>
        </div>

        <div className="space-y-4">
          {[
            { key: 'emailNotifications', label: '邮件通知', desc: '接收重要更新的邮件通知' },
            { key: 'pushNotifications', label: '推送通知', desc: '接收浏览器推送通知' },
            { key: 'taskUpdates', label: '任务更新', desc: '文章生成完成时通知' },
            { key: 'weeklyReport', label: '周报', desc: '每周发送使用统计报告' },
          ].map((item) => (
            <div key={item.key} className="flex items-center justify-between p-3 bg-background rounded-lg">
              <div>
                <h4 className="font-medium text-text-primary">{item.label}</h4>
                <p className="text-sm text-text-muted">{item.desc}</p>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={settings[item.key as keyof SettingsData] as boolean}
                  onChange={(e) => setSettings({ ...settings, [item.key]: e.target.checked })}
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary/20 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary"></div>
              </label>
            </div>
          ))}
        </div>
      </div>

      {/* 偏好设置 */}
      <div className="bg-card rounded-xl shadow-md p-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="p-2 bg-purple-100 rounded-lg">
            <Palette size={24} className="text-purple-500" />
          </div>
          <div>
            <h2 className="text-xl font-semibold text-text-primary">偏好设置</h2>
            <p className="text-sm text-text-muted">自定义您的使用体验</p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* 语言 */}
          <div>
            <label className="block text-sm font-medium text-text-primary mb-2">
              语言
            </label>
            <select
              value={settings.language}
              onChange={(e) => setSettings({ ...settings, language: e.target.value as any })}
              className="w-full px-4 py-2 rounded-lg border border-border focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
            >
              <option value="zh-CN">简体中文</option>
              <option value="en-US">English</option>
            </select>
          </div>

          {/* 主题 */}
          <div>
            <label className="block text-sm font-medium text-text-primary mb-2">
              主题
            </label>
            <select
              value={settings.theme}
              onChange={(e) => setSettings({ ...settings, theme: e.target.value as any })}
              className="w-full px-4 py-2 rounded-lg border border-border focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
            >
              <option value="light">浅色</option>
              <option value="dark">深色</option>
              <option value="auto">跟随系统</option>
            </select>
          </div>

          {/* 默认文章类型 */}
          <div>
            <label className="block text-sm font-medium text-text-primary mb-2">
              默认文章类型
            </label>
            <select
              value={settings.defaultArticleType}
              onChange={(e) => setSettings({ ...settings, defaultArticleType: e.target.value })}
              className="w-full px-4 py-2 rounded-lg border border-border focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
            >
              <option value="blog">博客文章</option>
              <option value="news">新闻报道</option>
              <option value="social_media">社交媒体</option>
              <option value="academic">学术论文</option>
              <option value="creative">创意写作</option>
            </select>
          </div>

          {/* 自动保存 */}
          <div className="flex items-center justify-between p-3 bg-background rounded-lg">
            <div>
              <h4 className="font-medium text-text-primary">自动保存</h4>
              <p className="text-sm text-text-muted">编辑时自动保存草稿</p>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={settings.autoSave}
                onChange={(e) => setSettings({ ...settings, autoSave: e.target.checked })}
                className="sr-only peer"
              />
              <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary/20 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary"></div>
            </label>
          </div>
        </div>
      </div>

      {/* API 设置 */}
      <div className="bg-card rounded-xl shadow-md p-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="p-2 bg-orange-100 rounded-lg">
            <Globe size={24} className="text-orange-500" />
          </div>
          <div>
            <h2 className="text-xl font-semibold text-text-primary">API 设置</h2>
            <p className="text-sm text-text-muted">配置第三方 API 密钥</p>
          </div>
        </div>

        <div className="space-y-4">
          {/* API Key */}
          <div>
            <label className="block text-sm font-medium text-text-primary mb-2">
              API 密钥
            </label>
            <div className="relative">
              <input
                type={showApiKey ? 'text' : 'password'}
                value={settings.apiKey}
                onChange={(e) => setSettings({ ...settings, apiKey: e.target.value })}
                placeholder="sk-..."
                className="w-full px-4 py-2 rounded-lg border border-border focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent pr-12"
              />
              <button
                onClick={() => setShowApiKey(!showApiKey)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted hover:text-primary"
              >
                {showApiKey ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </div>
            <p className="text-xs text-text-muted mt-1">用于 AI 功能的 OpenAI API 密钥</p>
          </div>

          {/* API Endpoint */}
          <div>
            <label className="block text-sm font-medium text-text-primary mb-2">
              API 端点
            </label>
            <input
              type="text"
              value={settings.apiEndpoint}
              onChange={(e) => setSettings({ ...settings, apiEndpoint: e.target.value })}
              className="w-full px-4 py-2 rounded-lg border border-border focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
            />
            <p className="text-xs text-text-muted mt-1">如果使用代理，请输入自定义端点</p>
          </div>
        </div>
      </div>

      {/* 帮助链接 */}
      <div className="bg-card rounded-xl shadow-md p-6">
        <h2 className="text-xl font-semibold text-text-primary mb-4">帮助与支持</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <a
            href="#"
            className="flex items-center gap-3 p-4 bg-background rounded-lg hover:border-primary border border-transparent transition-colors"
          >
            <HelpCircle size={20} className="text-primary" />
            <div>
              <h4 className="font-medium text-text-primary">帮助中心</h4>
              <p className="text-sm text-text-muted">查找常见问题</p>
            </div>
          </a>

          <a
            href="#"
            className="flex items-center gap-3 p-4 bg-background rounded-lg hover:border-primary border border-transparent transition-colors"
          >
            <CreditCard size={20} className="text-primary" />
            <div>
              <h4 className="font-medium text-text-primary">订阅管理</h4>
              <p className="text-sm text-text-muted">查看和升级计划</p>
            </div>
          </a>

          <a
            href="#"
            className="flex items-center gap-3 p-4 bg-background rounded-lg hover:border-primary border border-transparent transition-colors"
          >
            <Globe size={20} className="text-primary" />
            <div>
              <h4 className="font-medium text-text-primary">社区网站</h4>
              <p className="text-sm text-text-muted">访问创作者社区</p>
            </div>
          </a>
        </div>
      </div>

      {/* 保存按钮 */}
      <div className="flex justify-end gap-3">
        <button
          onClick={() => setSettings({
            displayName: user?.display_name || '',
            email: user?.email || '',
            avatar: user?.avatar || '',
            emailNotifications: true,
            pushNotifications: false,
            taskUpdates: true,
            weeklyReport: true,
            language: 'zh-CN',
            theme: 'light',
            defaultArticleType: 'blog',
            autoSave: true,
            apiKey: '',
            apiEndpoint: 'https://api.openai.com/v1',
          })}
          className="px-6 py-3 border border-border rounded-lg font-medium hover:bg-background transition-colors"
        >
          重置
        </button>

        <button
          onClick={handleSave}
          disabled={isSaving}
          className="px-6 py-3 bg-primary text-white rounded-lg font-medium hover:bg-primary-dark transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
        >
          <Save size={18} />
          <span>{isSaving ? '保存中...' : '保存设置'}</span>
        </button>
      </div>
    </div>
  )
}

export default Settings
