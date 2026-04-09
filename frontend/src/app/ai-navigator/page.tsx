import Link from 'next/link';
import MainLayout from '@/components/layout/MainLayout';

type NavCardItem = {
  icon: string;
  title: string;
  description: string;
  href: string;
  gradient: string;
  internal?: boolean;
};

type NavSection = {
  emoji: string;
  title: string;
  description: string;
  cards: NavCardItem[];
};

const quickLinks: NavCardItem[] = [
  {
    icon: '🤖',
    title: 'AI助手',
    description: '进入智能对话与创作辅助中心',
    href: '/ai-assistant',
    gradient: 'from-indigo-600 to-blue-600',
    internal: true,
  },
  {
    icon: '✍️',
    title: '文章创作',
    description: '进入完整写作流，生成长文与营销内容',
    href: '/writer',
    gradient: 'from-purple-600 to-pink-600',
    internal: true,
  },
  {
    icon: '📦',
    title: '批量生成',
    description: '批量创建写作任务，集中生产多篇文章',
    href: '/batch',
    gradient: 'from-amber-500 to-orange-500',
    internal: true,
  },
  {
    icon: '🔥',
    title: '热点中心',
    description: '查看热点并快速转化为选题线索',
    href: '/hotspots',
    gradient: 'from-rose-500 to-red-500',
    internal: true,
  },
];

const sections: NavSection[] = [
  {
    emoji: '🔍',
    title: '智能搜索引擎',
    description: '选择适合当前任务的搜索入口，快速获取资料、线索和榜单。',
    cards: [
      {
        icon: '🌐',
        title: '秘塔 AI 搜索',
        description: '国产智能搜索引擎，没有广告，适合做中文信息检索。',
        href: 'https://metaso.cn/',
        gradient: 'from-orange-500 to-red-500',
      },
      {
        icon: '🏆',
        title: 'LM Arena',
        description: '查看主流大模型排行榜与能力对比。',
        href: 'https://lmarena.ai/leaderboard',
        gradient: 'from-sky-500 to-cyan-500',
      },
      {
        icon: '🔎',
        title: 'DuckDuckGo',
        description: '轻量无登录搜索，适合快速查找公开网页。',
        href: 'https://duckduckgo.com/',
        gradient: 'from-violet-500 to-fuchsia-500',
      },
      {
        icon: '🧭',
        title: 'Tavily',
        description: '面向 AI 检索场景的搜索平台与 API 控制台。',
        href: 'https://app.tavily.com/',
        gradient: 'from-cyan-500 to-blue-500',
      },
      {
        icon: '⚡',
        title: 'Serper',
        description: 'Google 搜索 API 服务，适合自动化抓取与工作流集成。',
        href: 'https://serper.dev/',
        gradient: 'from-yellow-500 to-orange-500',
      },
      {
        icon: '📰',
        title: '热点中心',
        description: '回到站内热点汇总页，直接沉淀为创作选题。',
        href: '/hotspots',
        gradient: 'from-rose-500 to-red-500',
        internal: true,
      },
    ],
  },
  {
    emoji: '📰',
    title: '内容发布平台',
    description: '常用内容分发与创作者后台入口，发文和运营时可以直接跳转。',
    cards: [
      {
        icon: '🟢',
        title: '微信公众号',
        description: '最大的中文内容平台之一，适合深度文章发布。',
        href: 'https://mp.weixin.qq.com/',
        gradient: 'from-green-500 to-emerald-500',
      },
      {
        icon: '📣',
        title: '头条号',
        description: '今日头条内容创作平台，流量和分发能力强。',
        href: 'https://mp.toutiao.com/profile_v4/index',
        gradient: 'from-red-500 to-pink-500',
      },
      {
        icon: '📱',
        title: '知乎创作中心',
        description: '高质量问答社区，适合专业内容创作。',
        href: 'https://www.zhihu.com/creator',
        gradient: 'from-blue-500 to-cyan-500',
      },
      {
        icon: '📝',
        title: '百家号',
        description: '百度官方内容平台，适合搜索流量分发。',
        href: 'https://baijiahao.baidu.com',
        gradient: 'from-blue-600 to-indigo-500',
      },
      {
        icon: '📚',
        title: 'CSDN',
        description: '技术内容社区和创作者平台，适合开发类文章。',
        href: 'https://www.csdn.net/',
        gradient: 'from-red-600 to-orange-500',
      },
      {
        icon: '📊',
        title: '简书',
        description: '原创写作社区，适合长文分发与沉淀。',
        href: 'https://www.jianshu.com/',
        gradient: 'from-orange-500 to-red-400',
      },
    ],
  },
  {
    emoji: '🎬',
    title: 'AI 视频创作工具',
    description: '智能视频生成和编辑工具，适合把文字内容转成视频素材。',
    cards: [
      {
        icon: '🎞️',
        title: '海螺 AI',
        description: '文本一键生成精美视频，支持多种风格模板。',
        href: 'https://hailuoai.com/create',
        gradient: 'from-cyan-500 to-blue-500',
      },
      {
        icon: '🎥',
        title: '即梦',
        description: '字节系 AI 视频生成工具，适合短视频快速制作。',
        href: 'https://jimeng.jianying.com/ai-tool/home',
        gradient: 'from-rose-400 to-pink-500',
      },
      {
        icon: '✂️',
        title: '剪映',
        description: '专业视频剪辑工具，带 AI 创作能力。',
        href: 'https://www.jianying.com/ai-creator/start',
        gradient: 'from-teal-500 to-cyan-500',
      },
    ],
  },
  {
    emoji: '🛠️',
    title: '创作工具',
    description: '直接服务写作、配图和内容复盘的工作入口。',
    cards: [
      {
        icon: '✍️',
        title: '文章创作',
        description: '进入写作主流程，产出完整文章内容。',
        href: '/writer',
        gradient: 'from-purple-500 to-fuchsia-500',
        internal: true,
      },
      {
        icon: '📦',
        title: '批量生成',
        description: '一次创建多条主题任务，适合批量起稿。',
        href: '/batch',
        gradient: 'from-amber-500 to-orange-500',
        internal: true,
      },
      {
        icon: '📚',
        title: '历史记录',
        description: '查看已生成内容并继续编辑、下载或复用。',
        href: '/history',
        gradient: 'from-orange-500 to-rose-500',
        internal: true,
      },
      {
        icon: '💡',
        title: '推文选题',
        description: '快速生成社媒选题与标题灵感。',
        href: '/tweet-topics',
        gradient: 'from-yellow-500 to-amber-500',
        internal: true,
      },
      {
        icon: '🎨',
        title: 'LiblibAI',
        description: '常用 AI 生图平台，适合做配图和视觉素材。',
        href: 'https://www.liblib.art/',
        gradient: 'from-indigo-500 to-blue-500',
      },
      {
        icon: '🖼️',
        title: 'RunningHub',
        description: '国内生图平台，适合多风格图像生成。',
        href: 'https://www.runninghub.cn/',
        gradient: 'from-green-500 to-emerald-500',
      },
    ],
  },
  {
    emoji: '🧠',
    title: 'AI 模型平台',
    description: '常用模型控制台与对话平台入口，方便切模型和做能力验证。',
    cards: [
      {
        icon: '🧪',
        title: 'Google AI Studio',
        description: '谷歌模型与提示词试验平台。',
        href: 'https://aistudio.google.com/',
        gradient: 'from-blue-500 to-green-500',
      },
      {
        icon: '🤖',
        title: 'ChatGPT',
        description: '全球主流对话模型平台，适合通用创作与推理。',
        href: 'https://chatgpt.com/',
        gradient: 'from-sky-500 to-blue-500',
      },
      {
        icon: '🔎',
        title: 'DeepSeek 平台',
        description: '适合代码、推理与长文本场景。',
        href: 'https://platform.deepseek.com/usage',
        gradient: 'from-blue-600 to-indigo-500',
      },
      {
        icon: '🌙',
        title: 'Moonshot',
        description: '长上下文模型平台，适合资料汇总和长文理解。',
        href: 'https://platform.moonshot.cn/console/account',
        gradient: 'from-indigo-500 to-purple-500',
      },
      {
        icon: '✨',
        title: '通义千问',
        description: '中文模型生态较完整，适合国内场景测试。',
        href: 'https://chat.qwen.ai/',
        gradient: 'from-teal-500 to-cyan-500',
      },
      {
        icon: '🎯',
        title: 'MiniMax',
        description: '多模态能力强，适合文本、语音、视频场景。',
        href: 'https://www.minimaxi.com/',
        gradient: 'from-orange-500 to-yellow-500',
      },
    ],
  },
  {
    emoji: '💻',
    title: '算力与模型社区',
    description: '做部署、找模型、找算力时常用的站点。',
    cards: [
      {
        icon: '☁️',
        title: '共绩云 Serverless',
        description: '多地域 Serverless 与算力服务平台。',
        href: 'https://www.gongjiyun.com/product/serverless/',
        gradient: 'from-blue-500 to-cyan-500',
      },
      {
        icon: '🧮',
        title: 'CSDN GPU',
        description: 'GPU 云算力平台，适合大模型训练和推理。',
        href: 'https://gpu.csdn.net/',
        gradient: 'from-red-600 to-red-400',
      },
      {
        icon: '🖥️',
        title: '超算互联网',
        description: '算力与 AI 服务商城，一站式资源平台。',
        href: 'https://www.scnet.cn/ui/mall/',
        gradient: 'from-orange-500 to-red-500',
      },
      {
        icon: '🌐',
        title: 'ModelScope 魔搭',
        description: '阿里开源模型社区，找模型和案例都方便。',
        href: 'https://modelscope.cn/my/overview',
        gradient: 'from-sky-500 to-blue-500',
      },
      {
        icon: '🤗',
        title: 'Hugging Face',
        description: '全球最大的开源模型与数据集社区。',
        href: 'https://huggingface.co/',
        gradient: 'from-yellow-500 to-orange-500',
      },
      {
        icon: '🚀',
        title: 'Gitee AI',
        description: '国产开源平台的 AI 开发与部署入口。',
        href: 'https://ai.gitee.com/',
        gradient: 'from-pink-500 to-purple-500',
      },
    ],
  },
];

export default function AINavigatorPage() {
  return (
    <MainLayout>
      <div className="min-h-screen bg-gradient-to-br from-[#fff7ed] via-[#fff1f2] to-[#eff6ff] py-8 px-4">
        <div className="max-w-7xl mx-auto">
          <div className="rounded-[28px] bg-gradient-to-r from-[#7c3aed] via-[#4f46e5] to-[#2563eb] px-8 py-10 text-white shadow-xl mb-10">
            <p className="text-sm uppercase tracking-[0.24em] text-white/70 mb-3">Navigation Hub</p>
            <h1 className="text-4xl font-bold mb-3">🚀 内容创作导航中心</h1>
            <p className="text-lg text-white/90 max-w-3xl">
              把你之前常用的资源导航页恢复回来了。这里集中收纳搜索、发布、视频、模型和算力平台，方便一站式跳转。
            </p>
          </div>

          <section className="mb-12">
            <div className="flex items-center justify-between gap-4 mb-5">
              <div>
                <h2 className="text-2xl font-bold text-slate-900">常用入口</h2>
                <p className="text-slate-600 mt-1">先回到站内主流程，再按需要跳外部资源。</p>
              </div>
              <Link
                href="/workspace"
                className="rounded-full border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 hover:border-slate-400 hover:text-slate-900 transition"
              >
                返回工作台
              </Link>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-5">
              {quickLinks.map((item) => (
                <NavCard key={item.title} item={item} />
              ))}
            </div>
          </section>

          {sections.map((section) => (
            <section key={section.title} className="mb-12">
              <div className="mb-6 rounded-2xl border border-white/70 bg-white/80 px-6 py-5 shadow-sm backdrop-blur">
                <h2 className="text-2xl font-bold text-slate-900">
                  {section.emoji} {section.title}
                </h2>
                <p className="text-slate-600 mt-2">{section.description}</p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
                {section.cards.map((item) => (
                  <NavCard key={item.title} item={item} />
                ))}
              </div>
            </section>
          ))}

          <footer className="border-t border-slate-200 pt-8 pb-4 text-center text-slate-500">
            <p className="text-base font-semibold text-slate-700 mb-2">内容创作导航中心</p>
            <p className="text-sm">如果你还记得原来某个具体站点没补回来，我可以继续按你习惯的分类补齐。</p>
          </footer>
        </div>
      </div>
    </MainLayout>
  );
}

function NavCard({ item }: { item: NavCardItem }) {
  const content = (
    <div className="h-full rounded-3xl border border-slate-200 bg-white p-6 shadow-sm transition duration-200 hover:-translate-y-1 hover:shadow-xl">
      <div className="flex items-start justify-between gap-4 mb-5">
        <div className={`inline-flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-r ${item.gradient} text-3xl shadow-md`}>
          <span>{item.icon}</span>
        </div>
        <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600">
          {item.internal ? '站内' : '外链'}
        </span>
      </div>

      <h3 className="text-xl font-semibold text-slate-900 mb-2">{item.title}</h3>
      <p className="text-sm leading-6 text-slate-600 mb-6">{item.description}</p>

      <div className={`inline-flex items-center rounded-full bg-gradient-to-r ${item.gradient} px-4 py-2 text-sm font-semibold text-white`}>
        {item.internal ? '打开页面' : '进入平台'}
      </div>
    </div>
  );

  if (item.internal) {
    return (
      <Link href={item.href} className="block h-full">
        {content}
      </Link>
    );
  }

  return (
    <a href={item.href} target="_blank" rel="noopener noreferrer" className="block h-full">
      {content}
    </a>
  );
}
