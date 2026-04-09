'use client'

import Link from 'next/link'
import { useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { persistBackendAuth } from '@/lib/backend-auth-storage'
import { resolveAuthDestination } from '@/lib/auth-redirect'
import { getApiBaseUrl } from '@/lib/api-base-url'
import { LEGAL_LINKS } from '@/lib/legal-links'

const PRIMARY_DESTINATION = '/workspace'
const API_URL = getApiBaseUrl()

export default function SignInPage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const [isLoading, setIsLoading] = useState(false)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const authError = searchParams.get('error')
  const [error, setError] = useState(() => {
    if (authError === 'google') {
      return 'Google 登录暂时不可用，请稍后重试'
    }
    return ''
  })
  const callbackUrl = searchParams.get('callbackUrl')
  const destination = resolveAuthDestination(
    callbackUrl,
    typeof window === 'undefined' ? 'http://localhost:3000' : window.location.origin
  )
  const registerHref = callbackUrl
    ? `/auth/register?callbackUrl=${encodeURIComponent(callbackUrl)}`
    : '/auth/register'

  const handleGoogleSignIn = async () => {
    setError('')
    setIsLoading(true)

    try {
      const response = await fetch('/api/auth/csrf')
      if (!response.ok) {
        throw new Error('无法获取登录凭证')
      }

      const { csrfToken } = await response.json()
      if (!csrfToken) {
        throw new Error('登录凭证缺失')
      }

      const form = document.createElement('form')
      form.method = 'POST'
      form.action = '/api/auth/signin/google'
      form.style.display = 'none'

      const csrfInput = document.createElement('input')
      csrfInput.type = 'hidden'
      csrfInput.name = 'csrfToken'
      csrfInput.value = csrfToken
      form.appendChild(csrfInput)

      const callbackInput = document.createElement('input')
      callbackInput.type = 'hidden'
      callbackInput.name = 'callbackUrl'
      callbackInput.value = destination
      form.appendChild(callbackInput)

      document.body.appendChild(form)
      form.submit()
    } catch (error) {
      console.error('登录失败:', error)
      setError('Google 登录未能发起，请稍后重试')
      setIsLoading(false)
    }
  }

  const handleEmailSignIn = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setIsLoading(true)

    try {
      const response = await fetch(`${API_URL}/api/v1/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email, password }),
      })

      const data = await response.json()

      if (!response.ok) {
        setError(data.detail || '登录失败，请检查邮箱和密码')
        setIsLoading(false)
        return
      }

      persistBackendAuth(data.access_token, data.user)
      
      router.push(destination)
    } catch (error) {
      console.error('登录失败:', error)
      setError('网络错误，请稍后重试')
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-red-50 to-orange-50">
      <div data-testid="auth-primary-destination" data-path={destination} className="sr-only" />
      <div className="max-w-md w-full mx-4">
        {/* Logo 和标题 */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-2" style={{ fontFamily: 'Fredoka, sans-serif' }}>
            超能写
          </h1>
          <p className="text-gray-600" style={{ fontFamily: 'Nunito, sans-serif' }}>
            AI 驱动的智能写作平台
          </p>
        </div>

        {/* 登录卡片 */}
        <div className="bg-white rounded-2xl shadow-xl p-8">
          <h2 className="text-2xl font-semibold text-gray-900 mb-6 text-center">
            欢迎回来
          </h2>

          {/* Google 登录按钮 */}
          <button
            onClick={handleGoogleSignIn}
            disabled={isLoading}
            className="w-full flex items-center justify-center gap-3 bg-white border-2 border-gray-300 rounded-xl px-6 py-3 text-gray-700 font-semibold hover:bg-gray-50 hover:border-gray-400 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? (
              <div className="w-5 h-5 border-2 border-gray-300 border-t-gray-600 rounded-full animate-spin" />
            ) : (
              <svg className="w-5 h-5" viewBox="0 0 24 24">
                <path
                  fill="#4285F4"
                  d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
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
                  d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                />
              </svg>
            )}
            <span>使用 Google 账号登录</span>
          </button>

          {/* 分隔线 */}
          <div className="relative my-6">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-gray-300"></div>
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="px-2 bg-white text-gray-500">或</span>
            </div>
          </div>

          {/* 邮箱密码登录表单 */}
          <form onSubmit={handleEmailSignIn} className="space-y-4">
            {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
                {error}
              </div>
            )}

            <div>
              <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-2">
                邮箱地址
              </label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent outline-none transition-all"
                placeholder="your@email.com"
                disabled={isLoading}
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-2">
                密码
              </label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={8}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent outline-none transition-all"
                placeholder="••••••••"
                disabled={isLoading}
              />
            </div>

            <div className="flex items-center justify-between text-sm">
              <p className="text-primary">
                暂不支持密码找回，请联系管理员
              </p>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full bg-primary text-white rounded-lg px-6 py-3 font-semibold hover:bg-primary-dark transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? (
                <div className="flex items-center justify-center gap-2">
                  <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  <span>登录中...</span>
                </div>
              ) : (
                '登录'
              )}
            </button>
          </form>

          {/* 注册链接 */}
          <div className="mt-6 text-center text-sm text-gray-600">
            还没有账号？{' '}
            <Link href={registerHref} className="text-primary font-semibold hover:underline">
              立即注册
            </Link>
          </div>
        </div>

        {/* 底部信息 */}
          <div className="mt-8 text-center text-sm text-gray-600">
            <p>登录即表示您同意我们的</p>
            <p className="mt-1">
              <Link href={LEGAL_LINKS.terms} className="text-primary hover:underline">
                服务条款
              </Link>
              {' '}和{' '}
              <Link href={LEGAL_LINKS.privacy} className="text-primary hover:underline">
                隐私政策
              </Link>
            </p>
          </div>
      </div>
    </div>
  )
}
