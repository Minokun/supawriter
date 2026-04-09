import Link from 'next/link';
import MainLayout from '@/components/layout/MainLayout';
import Card from '@/components/ui/Card';
import Button from '@/components/ui/Button';

const features = [
  {
    icon: '🤖',
    title: 'AI 助手',
    description: '智能对话助手，随时帮你整理思路、生成灵感并辅助决策。',
    href: '/ai-assistant',
  },
  {
    icon: '✍️',
    title: '文章创作',
    description: '一键生成文章、博客和营销内容，快速进入完整写作流程。',
    href: '/writer',
  },
  {
    icon: '📦',
    title: '批量生成',
    description: '批量创建写作任务，一次生成多篇内容，适合专题运营和高频更新。',
    href: '/batch',
  },
  {
    icon: '💡',
    title: '推文选题',
    description: '基于热点和平台语境生成可执行的话题方向与标题灵感。',
    href: '/tweet-topics',
  },
];

const hotspots = [
  {
    source: '热点中心',
    title: '查看最新热点并快速转为写作选题',
    href: '/hotspots',
    time: '实时更新',
  },
  {
    source: '新闻资讯',
    title: '浏览科技、开源与实时新闻，补充选题背景',
    href: '/news',
    time: '资讯追踪',
  },
  {
    source: '全网热点',
    title: '聚合百度、微博、抖音等平台热点，快速找灵感',
    href: '/inspiration',
    time: '灵感发现',
  },
  {
    source: '历史记录',
    title: '回看近期生成内容并继续编辑优化',
    href: '/history',
    time: '最近创作',
  },
];

export default function WorkspacePage() {
  return (
    <MainLayout>
      <div className="max-w-[1376px] mx-auto">
        <div className="mb-8">
          <h1 className="font-heading text-[32px] font-semibold text-text-primary mb-3">
            创作空间
          </h1>
          <p className="font-body text-base text-text-secondary">
            从这里进入各类创作工具、热点线索和历史内容管理。
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
          {features.map((feature) => (
            <Card key={feature.title} hoverable padding="xl">
              <div className="flex flex-col h-full">
                <div className="w-16 h-16 bg-bg rounded-2xl flex items-center justify-center mb-4">
                  <span className="text-[28px]">{feature.icon}</span>
                </div>

                <h2 className="font-heading text-[22px] font-semibold text-text-primary mb-3">
                  {feature.title}
                </h2>

                <p className="font-body text-[15px] text-text-secondary leading-relaxed mb-6 flex-grow">
                  {feature.description}
                </p>

                <Link href={feature.href}>
                  <Button variant="secondary" size="md" className="w-full">
                    开始使用 →
                  </Button>
                </Link>
              </div>
            </Card>
          ))}
        </div>

        <Card padding="lg">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <span className="text-2xl">🧭</span>
              <h2 className="font-heading text-xl font-semibold text-text-primary">
                快速导航
              </h2>
            </div>
            <Link
              href="/hotspots"
              className="font-body text-[15px] font-medium text-primary hover:text-[#B91C1C] transition-colors"
            >
              查看热点 →
            </Link>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
            {hotspots.map((hotspot) => (
              <Link
                key={hotspot.title}
                href={hotspot.href}
                className="bg-bg rounded-2xl p-5 hover:shadow-light transition-shadow cursor-pointer block"
              >
                <div className="mb-3">
                  <span className="inline-block px-3 h-[26px] leading-[26px] bg-bg text-primary text-xs font-semibold rounded-sm">
                    {hotspot.source}
                  </span>
                </div>
                <h3 className="font-body text-[15px] font-semibold text-text-primary mb-3 line-clamp-2">
                  {hotspot.title}
                </h3>
                <p className="font-body text-[13px] text-text-secondary">
                  {hotspot.time}
                </p>
              </Link>
            ))}
          </div>
        </Card>
      </div>
    </MainLayout>
  );
}
