'use client';

import { useState, useEffect } from 'react';
import MainLayout from '@/components/layout/MainLayout';
import Card from '@/components/ui/Card';
import Button from '@/components/ui/Button';
import { RefreshCw, ExternalLink, TrendingUp } from 'lucide-react';
import { useToast } from '@/components/ui/ToastContainer';

interface NewsItem {
  title: string;
  url?: string;
  hot?: string;
  heat?: string;
  hot_score?: string;
  desc?: string;
  image?: string;
}

interface NewsResponse {
  items?: NewsItem[];
  error?: string;
}

type NewsSource = 'thepaper-tech' | 'opensource' | 'realtime' | 'sina-live';

const NEWS_SOURCES = [
  { id: 'thepaper-tech' as NewsSource, name: '澎湃科技', icon: '🧪' },
  { id: 'opensource' as NewsSource, name: '开源项目', icon: '⭐' },
  { id: 'realtime' as NewsSource, name: '实时新闻', icon: '⚡' },
  { id: 'sina-live' as NewsSource, name: '新浪直播', icon: '📺' },
];

const REFRESH_INTERVAL = 5 * 60 * 1000; // 5分钟

export default function NewsPage() {
  const [activeSource, setActiveSource] = useState<NewsSource>('thepaper-tech');
  const [newsData, setNewsData] = useState<Record<NewsSource, NewsItem[]>>({
    'thepaper-tech': [],
    'opensource': [],
    'realtime': [],
    'sina-live': [],
  });
  const [loading, setLoading] = useState<Record<NewsSource, boolean>>({
    'thepaper-tech': false,
    'opensource': false,
    'realtime': false,
    'sina-live': false,
  });
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());
  const [errors, setErrors] = useState<Record<NewsSource, string | null>>({
    'thepaper-tech': null,
    'opensource': null,
    'realtime': null,
    'sina-live': null,
  });
  const { showError, showSuccess } = useToast();

  const fetchNews = async (source: NewsSource, showToast = false) => {
    setLoading(prev => ({ ...prev, [source]: true }));
    setErrors(prev => ({ ...prev, [source]: null }));
    try {
      console.log(`Fetching news from: /api/news/${source}`);
      const response = await fetch(`/api/news/${source}`);
      console.log(`Response status: ${response.status}`);

      const data: NewsResponse = await response.json().catch(() => ({}));
      const items = Array.isArray(data.items) ? data.items : [];
      const hasExplicitError = Boolean(data.error && items.length === 0);

      if (!response.ok || hasExplicitError) {
        console.error(`Failed to fetch ${source}: ${response.status}`);
        setErrors(prev => ({ ...prev, [source]: '加载失败，请稍后重试' }));
        if (showToast) {
          showError('获取数据失败');
        }
        return;
      }

      console.log(`Received data for ${source}:`, data);
      console.log(`Setting ${items.length} items for ${source}`);
      setNewsData(prev => ({ ...prev, [source]: items }));
      setLastUpdate(new Date());
      if (showToast) {
        showSuccess('数据已更新');
      }
    } catch (error) {
      console.error(`获取${source}数据失败:`, error);
      setErrors(prev => ({ ...prev, [source]: '加载失败，请稍后重试' }));
      if (showToast) {
        showError('获取数据失败');
      }
    } finally {
      setLoading(prev => ({ ...prev, [source]: false }));
    }
  };

  // 初始加载
  useEffect(() => {
    fetchNews(activeSource);
  }, [activeSource]);

  // 5分钟自动刷新
  useEffect(() => {
    const interval = setInterval(() => {
      fetchNews(activeSource);
    }, REFRESH_INTERVAL);

    return () => clearInterval(interval);
  }, [activeSource]);

  const handleRefresh = () => {
    fetchNews(activeSource, true);
  };

  const currentNews = newsData[activeSource];
  const isLoading = loading[activeSource];
  const currentError = errors[activeSource];

  return (
    <MainLayout>
      <div className="max-w-[1376px] mx-auto">
        {/* 头部 */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-3">
            <span className="text-[32px]">📰</span>
            <div>
              <h1 className="font-heading text-[32px] font-semibold text-text-primary">
                热点资讯
              </h1>
              <p className="font-body text-base text-text-secondary mt-1">
                实时追踪全网热点，5分钟自动更新
              </p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-sm text-text-secondary">
              更新于 {lastUpdate.toLocaleTimeString()}
            </span>
            <Button
              variant="secondary"
              size="sm"
              icon={<RefreshCw size={16} className={isLoading ? 'animate-spin' : ''} />}
              onClick={handleRefresh}
              disabled={isLoading}
            >
              刷新
            </Button>
          </div>
        </div>

        {/* 来源选择 */}
        <div className="flex gap-2 mb-6">
          {NEWS_SOURCES.map(source => (
            <button
              key={source.id}
              onClick={() => setActiveSource(source.id)}
              className={`flex items-center gap-2 h-10 px-5 rounded-lg font-body text-[15px] font-semibold transition-all ${
                activeSource === source.id
                  ? 'bg-primary text-white'
                  : 'bg-transparent border-[1.5px] border-border text-text-secondary hover:border-primary'
              }`}
            >
              <span>{source.icon}</span>
              {source.name}
            </button>
          ))}
        </div>

        {/* 新闻列表 */}
        <Card padding="sm">
          {isLoading && currentNews.length === 0 ? (
            <div className="flex items-center justify-center py-12">
              <RefreshCw className="animate-spin text-primary" size={40} />
            </div>
          ) : currentError ? (
            <div className="text-center py-12">
              <p className="text-red-600 text-base font-medium">{currentError}</p>
            </div>
          ) : currentNews.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-text-secondary text-base">暂无数据</p>
            </div>
          ) : (
            <div className="space-y-2">
              {currentNews.map((item, index) => (
                <div
                  key={index}
                  className="flex items-start gap-3 p-2.5 bg-bg rounded-lg hover:bg-surface transition-colors border-[1.5px] border-transparent hover:border-primary"
                >
                  {/* 排名 */}
                  <div
                    className={`flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center font-heading font-bold text-xs ${
                      index < 3
                        ? 'bg-primary text-white'
                        : 'bg-border text-text-secondary'
                    }`}
                  >
                    {index + 1}
                  </div>

                  {/* 图片 */}
                  {item.image && (
                    <img
                      src={item.image}
                      alt={item.title}
                      className="flex-shrink-0 w-24 h-16 object-cover rounded-md"
                      referrerPolicy="no-referrer"
                      onError={(e) => {
                        e.currentTarget.style.display = 'none';
                      }}
                    />
                  )}

                  {/* 内容 */}
                  <div className="flex-1 min-w-0">
                    <h3 className="font-body text-sm font-semibold text-text-primary mb-0.5 line-clamp-2 leading-snug">
                      {item.title}
                    </h3>
                    {item.desc && (
                      <p className="text-xs text-text-secondary line-clamp-1 mb-1 leading-relaxed">
                        {item.desc}
                      </p>
                    )}
                    <div className="flex items-center gap-2">
                      {(item.hot || item.heat || item.hot_score) && (
                        <span className="flex items-center gap-0.5 text-xs text-error font-medium">
                          <TrendingUp size={12} />
                          {item.hot || item.heat || item.hot_score}
                        </span>
                      )}
                    </div>
                  </div>

                  {/* 链接 */}
                  {item.url && (
                    <a
                      href={item.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex-shrink-0 text-text-secondary hover:text-primary transition-colors"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <ExternalLink size={18} />
                    </a>
                  )}
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>
    </MainLayout>
  );
}
