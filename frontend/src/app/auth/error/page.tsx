'use client'

import { useSearchParams } from 'next/navigation'
import Link from 'next/link'
import { Suspense } from 'react'

function AuthErrorContent() {
  const searchParams = useSearchParams()
  const error = searchParams.get('error')

  const errorMessages: Record<string, string> = {
    Configuration: '服务器配置错误，请联系管理员',
    AccessDenied: '访问被拒绝，您可能没有权限',
    Verification: '验证失败，请重试',
    Default: '登录过程中出现错误，请重试',
  }

  const errorMessage = errorMessages[error || 'Default'] || errorMessages.Default

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-red-50 to-orange-50">
      <div className="max-w-md w-full mx-4">
        <div className="bg-white rounded-2xl shadow-xl p-8 text-center">
          <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </div>

          <h1 className="text-2xl font-bold text-gray-900 mb-2">登录失败</h1>
          <p className="text-gray-600 mb-6">{errorMessage}</p>

          <div className="space-y-3">
            <Link
              href="/auth/signin"
              className="block w-full bg-primary text-white rounded-xl px-6 py-3 font-semibold hover:bg-primary-dark transition-colors"
            >
              重新登录
            </Link>
            <Link
              href="/"
              className="block w-full bg-gray-100 text-gray-700 rounded-xl px-6 py-3 font-semibold hover:bg-gray-200 transition-colors"
            >
              返回首页
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}

export default function AuthErrorPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-red-50 to-orange-50">
        <div className="text-gray-600">加载中...</div>
      </div>
    }>
      <AuthErrorContent />
    </Suspense>
  )
}
