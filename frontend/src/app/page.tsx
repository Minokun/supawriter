import Link from 'next/link'

export default function HomePage() {
  return (
    <main
      aria-label="public landing hero"
      className="min-h-screen bg-slate-50 px-4 py-16 flex items-center justify-center"
    >
      <div className="max-w-3xl text-center space-y-6">
        <p className="text-sm uppercase tracking-[0.3em] text-primary/80">Supawriter</p>
        <h1 className="text-4xl sm:text-5xl font-bold text-gray-900">写作更快，更清晰，更有声量</h1>
        <p className="text-lg text-gray-600 leading-relaxed">
          为内容创作者提供一站式选题、创作与排期协助。无论是个人写手还是团队，都可以在这里
          体验 AI 助力的灵感流、安全协作与精细化分发。
        </p>
        <div className="flex flex-col gap-3 sm:flex-row sm:justify-center">
          <Link
            href="/auth/signin"
            className="px-6 py-3 rounded-xl bg-primary text-white font-semibold shadow hover:bg-primary-dark transition"
          >
            立即登录开始写作
          </Link>
          <Link
            href="/auth/register"
            className="px-6 py-3 rounded-xl border border-gray-300 text-gray-700 font-semibold hover:border-gray-400 transition"
          >
            免费注册体验
          </Link>
        </div>
      </div>
    </main>
  )
}
