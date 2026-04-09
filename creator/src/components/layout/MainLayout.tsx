import { Outlet, Link, useNavigate } from 'react-router-dom'
import { useAuthStore } from '@store/authStore'
import {
  Home,
  PenTool,
  MessageSquare,
  Lightbulb,
  History,
  Newspaper,
  Twitter,
  Settings,
  LogOut,
} from 'lucide-react'

function MainLayout() {
  const navigate = useNavigate()
  const { user, logout } = useAuthStore()

  const handleLogout = async () => {
    await logout()
    navigate('/auth/login')
  }

  const navigation = [
    { name: '工作台', href: '/workspace', icon: Home },
    { name: '超能写手', href: '/writer', icon: PenTool },
    { name: 'AI 助手', href: '/ai-chat', icon: MessageSquare },
    { name: '灵感发现', href: '/inspiration', icon: Lightbulb },
    { name: '新闻资讯', href: '/news', icon: Newspaper },
    { name: '推文选题', href: '/tweet-topics', icon: Twitter },
    { name: '历史记录', href: '/history', icon: History },
  ]

  return (
    <div className="min-h-screen bg-background">
      {/* 顶部导航栏 */}
      <header className="bg-card border-b border-border sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            {/* Logo */}
            <Link to="/workspace" className="flex items-center gap-2">
              <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center">
                <span className="text-white font-bold">超</span>
              </div>
              <span className="text-xl font-bold text-primary">超能写手</span>
            </Link>

            {/* 导航 */}
            <nav className="hidden md:flex items-center space-x-1">
              {navigation.map((item) => (
                <Link
                  key={item.name}
                  to={item.href}
                  className="flex items-center gap-2 px-4 py-2 rounded-lg text-text-secondary hover:text-primary hover:bg-background transition-colors"
                >
                  <item.icon size={20} />
                  <span>{item.name}</span>
                </Link>
              ))}
            </nav>

            {/* 用户菜单 */}
            <div className="flex items-center gap-4">
              {/* 社区网站链接 */}
              <a
                href="http://localhost:3001"
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-2 px-4 py-2 rounded-lg text-text-secondary hover:text-primary hover:bg-background transition-colors"
              >
                <Newspaper size={20} />
                <span className="hidden sm:inline">社区网站</span>
              </a>

              {/* 用户信息 */}
              <div className="flex items-center gap-3">
                <div className="text-right hidden sm:block">
                  <p className="text-sm font-medium text-text-primary">
                    {user?.display_name || user?.username}
                  </p>
                  <p className="text-xs text-text-muted">{user?.email}</p>
                </div>
                {user?.avatar ? (
                  <img
                    src={user.avatar}
                    alt={user.display_name || user.username}
                    className="w-10 h-10 rounded-full"
                  />
                ) : (
                  <div className="w-10 h-10 rounded-full bg-primary text-white flex items-center justify-center font-medium">
                    {(user?.display_name || user?.username || 'U').charAt(0).toUpperCase()}
                  </div>
                )}
              </div>

              {/* 设置按钮 */}
              <Link
                to="/settings"
                className="p-2 rounded-lg hover:bg-background transition-colors"
              >
                <Settings size={20} className="text-text-secondary" />
              </Link>

              {/* 登出按钮 */}
              <button
                onClick={handleLogout}
                className="p-2 rounded-lg hover:bg-background transition-colors"
              >
                <LogOut size={20} className="text-text-secondary" />
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* 移动端导航 */}
      <nav className="md:hidden fixed bottom-0 left-0 right-0 bg-card border-t border-border z-10">
        <div className="flex items-center justify-around py-2">
          {navigation.map((item) => (
            <Link
              key={item.name}
              to={item.href}
              className="flex flex-col items-center gap-1 px-4 py-2 text-text-secondary hover:text-primary transition-colors"
            >
              <item.icon size={20} />
              <span className="text-xs">{item.name}</span>
            </Link>
          ))}
        </div>
      </nav>

      {/* 主内容区 */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 pb-20 md:pb-8">
        <Outlet />
      </main>
    </div>
  )
}

export default MainLayout
