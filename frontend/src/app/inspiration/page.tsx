'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import MainLayout from '@/components/layout/MainLayout';
import Card from '@/components/ui/Card';
import Button from '@/components/ui/Button';
import Link from 'next/link';
import { Loader2, RefreshCw, TrendingUp, Newspaper, Flame } from 'lucide-react';

interface HotspotItem {
  title: string;
  url?: string;
  hot?: string;
  heat?: string;
  hot_score?: string;
  hot_value?: string;
  desc?: string;
  image?: string;
}

interface HotspotSource {
  id: string;
  name: string;
  icon: string;
}

const HOTSPOT_SOURCES: HotspotSource[] = [
  { id: 'thepaper', name: '澎湃热点', icon: '📰' },
  { id: '36kr', name: '36Kr创投', icon: '💼' },
  { id: 'baidu', name: '百度热搜', icon: '🔍' },
  { id: 'weibo', name: '微博热搜', icon: '📱' },
  { id: 'douyin', name: '抖音热搜', icon: '🎵' },
  { id: 'bilibili', name: 'B站', icon: '📹' },
  { id: 'toutiao', name: '今日头条', icon: '📲' },
];

const REFRESH_INTERVAL = 5 * 60 * 1000;

export default function InspirationPage() {
  const router = useRouter();
  const [sources] = useState<HotspotSource[]>(HOTSPOT_SOURCES);
  const [currentSource, setCurrentSource] = useState('baidu');
  const [hotspots, setHotspots] = useState<HotspotItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [fromCache, setFromCache] = useState(false);

  useEffect(() => {
    if (currentSource) {
      loadHotspots(currentSource);
    }
  }, [currentSource]);

  useEffect(() => {
    const interval = setInterval(() => {
      if (currentSource) {
        loadHotspots(currentSource);
      }
    }, REFRESH_INTERVAL);

    return () => clearInterval(interval);
  }, [currentSource]);

  const loadHotspots = async (source: string) => {
    setLoading(true);
    try {
      const response = await fetch(`/api/news/${source}`);
      if (!response.ok) {
        setHotspots([]);
        return;
      }
      const data = await response.json();
      setHotspots(data.items || []);
      setFromCache(Boolean(data.cached));
    } catch (error) {
      console.error('加载全网热点失败:', error);
      setHotspots([]);
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    await loadHotspots(currentSource);
    setRefreshing(false);
  };

  const handleCreateArticle = (hotspot: HotspotItem) => {
    const params = new URLSearchParams();
    params.set('topic', hotspot.title);
    params.set('source', 'hotspot');
    if (hotspot.url) {
      params.set('urls', hotspot.url);
    }
    router.push(`/writer?${params.toString()}`);
  };

  return (
    <MainLayout>
      <div className="max-w-[1376px] mx-auto">
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-3">
            <span className="text-[32px]">💡</span>
            <div>
              <h1 className="font-heading text-[32px] font-semibold text-text-primary">
                全网热点
              </h1>
              <p className="font-body text-base text-text-secondary mt-1">
                聚合多个平台热点，适合快速扫灵感、定方向、起选题。
              </p>
            </div>
          </div>
          <Button
            icon={<RefreshCw size={18} className={refreshing ? 'animate-spin' : ''} />}
            variant="primary"
            size="md"
            onClick={handleRefresh}
            disabled={refreshing}
          >
            {refreshing ? '刷新中...' : '刷新'}
          </Button>
        </div>

        <Card padding="md" className="mb-6">
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div>
              <h2 className="font-heading text-lg font-semibold text-text-primary">热点资讯分区</h2>
              <p className="text-sm text-text-secondary mt-1">
                这里偏向广域扫热点，想看结构化榜单去热点中心，想看专题流去新闻资讯。
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Link href="/hotspots" className="inline-flex items-center gap-2 rounded-lg border border-border bg-white px-4 py-2 text-sm font-semibold text-text-primary hover:border-primary">
                <Flame size={16} />
                热点中心
              </Link>
              <Link href="/news" className="inline-flex items-center gap-2 rounded-lg border border-border bg-white px-4 py-2 text-sm font-semibold text-text-primary hover:border-primary">
                <Newspaper size={16} />
                新闻资讯
              </Link>
              <Link href="/inspiration" className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white">
                <TrendingUp size={16} />
                全网热点
              </Link>
            </div>
          </div>
        </Card>

        <div className="flex gap-2 mb-6 overflow-x-auto pb-2">
          {sources.map((source) => (
            <button
              key={source.id}
              onClick={() => setCurrentSource(source.id)}
              className={`h-10 px-5 rounded-lg font-body text-[15px] font-semibold transition-all whitespace-nowrap ${
                currentSource === source.id
                  ? 'bg-primary text-white'
                  : 'bg-transparent border-[1.5px] border-border text-text-secondary hover:border-primary'
              }`}
            >
              {source.icon} {source.name}
            </button>
          ))}
        </div>

        {fromCache && !loading && (
          <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg flex items-center gap-2">
            <TrendingUp className="text-blue-500" size={16} />
            <span className="text-sm text-blue-700">当前结果来自缓存，点击刷新可拉取新数据。</span>
          </div>
        )}

        {loading ? (
          <Card padding="md">
            <div className="flex flex-col items-center justify-center py-10">
              <Loader2 className="animate-spin text-primary mb-3" size={40} />
              <p className="text-text-secondary text-sm">加载热点中...</p>
            </div>
          </Card>
        ) : hotspots.length === 0 ? (
          <Card padding="md">
            <div className="text-center py-10">
              <div className="text-5xl mb-3">🔍</div>
              <h3 className="font-heading text-lg font-semibold text-text-primary mb-2">暂无热点数据</h3>
              <p className="font-body text-text-secondary text-sm mb-3">请尝试切换其他热点源或刷新页面。</p>
              <Button variant="primary" size="sm" onClick={handleRefresh}>
                重新加载
              </Button>
            </div>
          </Card>
        ) : (
          <Card padding="sm">
            {hotspots.map((hotspot, index) => (
              <div
                key={`${hotspot.title}-${index}`}
                className={`flex items-center gap-3 p-2.5 hover:bg-bg transition-colors ${
                  index < hotspots.length - 1 ? 'border-b border-border' : ''
                }`}
              >
                <div
                  className={`w-7 h-7 rounded-lg flex items-center justify-center font-body text-sm font-semibold flex-shrink-0 ${
                    index < 3 ? 'bg-primary text-white' : 'bg-white border-2 border-primary text-primary'
                  }`}
                >
                  {index + 1}
                </div>

                {hotspot.image && (
                  <img
                    src={hotspot.image}
                    alt={hotspot.title}
                    className="flex-shrink-0 w-20 h-14 object-cover rounded-md"
                    referrerPolicy="no-referrer"
                    onError={(e) => {
                      e.currentTarget.style.display = 'none';
                    }}
                  />
                )}

                <div className="flex-grow min-w-0">
                  <h3 className="font-body text-sm font-semibold text-text-primary mb-1 line-clamp-2 leading-snug">
                    {hotspot.title}
                  </h3>
                  <div className="flex items-center gap-2 flex-wrap">
                    {hotspot.hot_score && (
                      <span className="text-xs px-2 py-0.5 bg-primary/10 text-primary rounded-full font-medium">🔥 {hotspot.hot_score}</span>
                    )}
                    {hotspot.heat && (
                      <span className="text-xs px-2 py-0.5 bg-secondary/10 text-secondary rounded-full font-medium">热度 {hotspot.heat}</span>
                    )}
                    {hotspot.hot_value && (
                      <span className="text-xs px-2 py-0.5 bg-border text-text-secondary rounded-full font-medium">热度 {hotspot.hot_value}</span>
                    )}
                    {hotspot.hot && (
                      <span className="text-xs px-2 py-0.5 bg-error/10 text-error rounded-full font-medium">{hotspot.hot}</span>
                    )}
                    {hotspot.url && (
                      <a
                        href={hotspot.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="font-body text-xs text-primary hover:underline"
                      >
                        查看详情 →
                      </a>
                    )}
                  </div>
                </div>

                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => handleCreateArticle(hotspot)}
                  className="flex-shrink-0"
                >
                  ✍️ 写这个
                </Button>
              </div>
            ))}
          </Card>
        )}
      </div>
    </MainLayout>
  );
}
