import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Eye, EyeOff } from 'lucide-react'
import { useAuthStore } from '@store/authStore'

function Login() {
  const navigate = useNavigate()
  const { login, register, isLoading, error, clearError } = useAuthStore()

  const [isLogin, setIsLogin] = useState(true)
  const [showPassword, setShowPassword] = useState(false)
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
  })

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    try {
      clearError()

      if (isLogin) {
        await login(formData.email, formData.password)
      } else {
        await register(formData.username, formData.email, formData.password)
      }

      // 登录/注册成功后跳转
      navigate('/workspace')
    } catch (err) {
      // 错误已在 store 中处理
      console.error('Auth error:', err)
    }
  }

  const handleGoogleLogin = () => {
    const frontend = 'creator'
    const apiUrl = import.meta.env.VITE_API_URL || '/api/v1'
    window.location.href = `${apiUrl}/auth/oauth/google?frontend=${frontend}`
  }

  const handleWechatLogin = () => {
    const frontend = 'creator'
    const apiUrl = import.meta.env.VITE_API_URL || '/api/v1'
    window.location.href = `${apiUrl}/auth/oauth/wechat?frontend=${frontend}`
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-background px-4">
      <div className="max-w-md w-full">
        {/* Logo */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-primary mb-2">超能写手</h1>
          <p className="text-text-secondary">AI 驱动的文章创作工具</p>
        </div>

        {/* 登录卡片 */}
        <div className="bg-card rounded-2xl shadow-lg p-8">
          {/* 标签切换 */}
          <div className="flex mb-6 bg-background rounded-lg p-1">
            <button
              onClick={() => { setIsLogin(true); clearError() }}
              className={`flex-1 py-2 rounded-md transition-colors ${
                isLogin
                  ? 'bg-primary text-white'
                  : 'text-text-secondary hover:text-primary'
              }`}
            >
              登录
            </button>
            <button
              onClick={() => { setIsLogin(false); clearError() }}
              className={`flex-1 py-2 rounded-md transition-colors ${
                !isLogin
                  ? 'bg-primary text-white'
                  : 'text-text-secondary hover:text-primary'
              }`}
            >
              注册
            </button>
          </div>

          {/* 错误提示 */}
          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-600 rounded-lg text-sm">
              {error}
            </div>
          )}

          {/* 表单 */}
          <form onSubmit={handleSubmit} className="space-y-4">
            {!isLogin && (
              <div>
                <label className="block text-sm font-medium text-text-primary mb-2">
                  用户名
                </label>
                <input
                  type="text"
                  value={formData.username}
                  onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                  className="w-full px-4 py-3 rounded-lg border border-border focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
                  placeholder="请输入用户名"
                  required={!isLogin}
                />
              </div>
            )}

            <div>
              <label className="block text-sm font-medium text-text-primary mb-2">
                邮箱
              </label>
              <input
                type="email"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                className="w-full px-4 py-3 rounded-lg border border-border focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
                placeholder="请输入邮箱地址"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-text-primary mb-2">
                密码
              </label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={formData.password}
                  onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                  className="w-full px-4 py-3 rounded-lg border border-border focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent pr-12"
                  placeholder="请输入密码"
                  required
                  minLength={8}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted hover:text-primary"
                >
                  {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full bg-primary text-white py-3 rounded-lg font-medium hover:bg-primary-dark transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? '处理中...' : isLogin ? '登录' : '注册'}
            </button>
          </form>

          {/* 分隔线 */}
          <div className="my-6 flex items-center">
            <div className="flex-1 border-t border-border"></div>
            <span className="px-4 text-sm text-text-muted">或</span>
            <div className="flex-1 border-t border-border"></div>
          </div>

          {/* OAuth 登录 */}
          <div className="space-y-3">
            <button
              type="button"
              onClick={handleGoogleLogin}
              className="w-full flex items-center justify-center gap-3 px-4 py-3 border border-border rounded-lg hover:bg-background transition-colors"
            >
              <svg className="w-5 h-5" viewBox="0 0 24 24">
                <path
                  fill="#4285F4"
                  d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 2.92v2.77h3.57c2.08-1.92 3.28-4.74 3.28-7.7z"
                />
                <path
                  fill="#34A853"
                  d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                />
                <path
                  fill="#FBBC05"
                  d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                />
                <path
                  fill="#EA4335"
                  d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66-2.84c.81-.62 1.84-1 4.21-1.64z"
                />
              </svg>
              使用 Google 继续
            </button>

            <button
              type="button"
              onClick={handleWechatLogin}
              className="w-full flex items-center justify-center gap-3 px-4 py-3 border border-border rounded-lg hover:bg-background transition-colors"
            >
              <svg className="w-5 h-5" viewBox="0 0 24 24" fill="#07C160">
                <path d="M8.691 2.188C3.891 2.188 0 5.668 0 8.016c0 2.347 3.891 2.347 8.691 2.347 2.068 0 4.053-.155 5.855-.425l.156-.027.266 4.344-.156 6.48-.027 2.133.156 6.5.109 6.5-4.762 0-7.262-3.461-7.262-7.744 0-.412.031-.805.09-1.175l-4.238.703c.78-2.531 3.5-4.375 6.578-4.375 4.016 0 7.262 3.461 7.262 7.734 0 .422-.031.809-.094 1.175l4.238-.719c-.78 2.531-3.5 4.375-6.578 4.375z" />
              </svg>
              使用微信登录
            </button>
          </div>

          {/* 提示 */}
          <p className="mt-6 text-center text-sm text-text-muted">
            {isLogin ? '还没有账号？' : '已有账号？'}
            <button
              type="button"
              onClick={() => { setIsLogin(!isLogin); clearError() }}
              className="ml-1 text-primary hover:underline"
            >
              {isLogin ? '立即注册' : '立即登录'}
            </button>
          </p>
        </div>

        {/* 底部链接 */}
        <div className="text-center mt-6 text-sm text-text-muted">
          <a href="http://localhost:3001" className="hover:text-primary">
            访问社区网站 →
          </a>
        </div>
      </div>
    </div>
  )
}

export default Login
