import Link from 'next/link'
import { LEGAL_LINKS } from '@/lib/legal-links'

export default function PrivacyPage() {
  return (
    <main className="min-h-screen bg-slate-50 px-6 py-16">
      <div className="mx-auto max-w-3xl rounded-2xl bg-white p-8 shadow-sm">
        <h1 className="text-3xl font-bold text-gray-900">隐私政策</h1>
        <p className="mt-4 text-sm leading-7 text-gray-600">
          本页为站内隐私政策占位页，用于确保公开认证链路中的隐私链接可访问、可验证。正式版本上线前，
          平台仅按提供服务所必需的最小范围处理账户与使用数据。
        </p>
        <div className="mt-8 space-y-4 text-sm leading-7 text-gray-700">
          <p>1. 登录信息仅用于身份认证、权限校验与基础产品运营。</p>
          <p>2. 使用记录和生成内容可能被用于故障排查、配额统计与体验优化。</p>
          <p>3. 如您需要删除或导出个人数据，请联系平台管理员处理。</p>
        </div>
        <div className="mt-8 flex gap-3">
          <Link href="/auth/signin" className="rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white">
            返回登录
          </Link>
          <Link href={LEGAL_LINKS.terms} className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-semibold text-gray-700">
            查看服务条款
          </Link>
        </div>
      </div>
    </main>
  )
}
