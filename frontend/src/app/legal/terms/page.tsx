import Link from 'next/link'
import { LEGAL_LINKS } from '@/lib/legal-links'

export default function TermsPage() {
  return (
    <main className="min-h-screen bg-slate-50 px-6 py-16">
      <div className="mx-auto max-w-3xl rounded-2xl bg-white p-8 shadow-sm">
        <h1 className="text-3xl font-bold text-gray-900">服务条款</h1>
        <p className="mt-4 text-sm leading-7 text-gray-600">
          本页为站内服务条款占位页，用于承接登录、注册和公开页面中的法务链接。在正式条款发布前，
          您继续使用 Supawriter 即表示理解当前产品仍处于持续迭代阶段。
        </p>
        <div className="mt-8 space-y-4 text-sm leading-7 text-gray-700">
          <p>1. 请勿上传违法、侵权或敏感内容，并对您提交的内容负责。</p>
          <p>2. 平台生成能力、会员权益与配额可能随产品迭代调整，以站内说明为准。</p>
          <p>3. 如需法务或数据相关支持，请联系平台管理员获取最新说明。</p>
        </div>
        <div className="mt-8 flex gap-3">
          <Link href="/auth/signin" className="rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white">
            返回登录
          </Link>
          <Link href={LEGAL_LINKS.privacy} className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-semibold text-gray-700">
            查看隐私政策
          </Link>
        </div>
      </div>
    </main>
  )
}
