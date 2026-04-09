'use client';

import { useState, useEffect } from 'react';
import MainLayout from '@/components/layout/MainLayout';
import Card from '@/components/ui/Card';
import Button from '@/components/ui/Button';
import Badge from '@/components/ui/Badge';
import Link from 'next/link';
import { useAuth } from '@/hooks/useAuth';
import { Loader2, RefreshCw, TrendingUp, Database, Clock, ExternalLink, Pause, Play, Newspaper, Lightbulb } from 'lucide-react';

interface HotspotSource {
  id: string;
  name: string;
  icon?: string;
  category?: string;
  enabled: boolean;
}

interface HotspotItem {
  id: number;
  title: string;
  url?: string;
  source: string;
  rank: number;
  rank_prev?: number;
  rank_change: number;
  hot_value?: number;
  is_new: boolean;
  description?: string;
  updated_at: string;
}

interface SourceData {
  source: string;
  updated_at: string;
  items: HotspotItem[];
  count: number;
}

const AUTO_REFRESH_INTERVAL = 5 * 60 * 1000; // 5分钟

export default function HotspotsPage() {
  const { getAuthHeaders, isAdmin } = useAuth();
  const [sources, setSources] = useState<HotspotSource[]>([]);
  const [currentSource, setCurrentSource] = useState<string>('baidu');
  const [sourceData, setSourceData] = useState<SourceData | null>(null);
  const [allData, setAllData] = useState<Record<string, SourceData>>({});
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [syncResults, setSyncResults] = useState<Record<string, { success: boolean; created: number; updated: number }>>({});
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [countdown, setCountdown] = useState(300); // 倒计时秒数
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // 加载平台列表
  useEffect(() => {
    loadSources();
  }, []);

  // 加载当前平台数据
  useEffect(() => {
    if (currentSource) {
      loadSourceData(currentSource);
      setCountdown(300); // 切换平台时重置倒计时
    }
  }, [currentSource]);

  // 自动刷新
  useEffect(() => {
    if (!autoRefresh || !currentSource) return;

    const interval = setInterval(() => {
      loadSourceData(currentSource);
      setCountdown(300);
    }, AUTO_REFRESH_INTERVAL);

    return () => clearInterval(interval);
  }, [autoRefresh, currentSource]);

  // 倒计时
  useEffect(() => {
    if (!autoRefresh) return;

    const timer = setInterval(() => {
      setCountdown(prev => (prev > 0 ? prev - 1 : 300));
    }, 1000);

    return () => clearInterval(timer);
  }, [autoRefresh]);

  const loadSources = async () => {
    try {
      const response = await fetch('/api/hotspots/v2/sources');
      if (response.ok) {
        const data = await response.json();
        setSources(data.sources || []);
      } else {
        setSources([]);
        setErrorMessage('热点数据源暂时不可用，请稍后重试');
      }
    } catch (error) {
      console.error('加载平台列表失败:', error);
      setSources([]);
      setErrorMessage('热点数据源暂时不可用，请稍后重试');
    }
  };

  const loadSourceData = async (source: string) => {
    setLoading(true);
    setErrorMessage(null);
    try {
      const response = await fetch(`/api/hotspots/v2/latest/${source}?limit=50`);
      if (response.ok) {
        const data = await response.json();
        setSourceData(data);
      } else {
        setSourceData(null);
        setErrorMessage('热点数据加载失败，请稍后重试');
      }
    } catch (error) {
      console.error('加载热点数据失败:', error);
      setSourceData(null);
      setErrorMessage('热点数据加载失败，请稍后重试');
    } finally {
      setLoading(false);
    }
  };

  const loadAllData = async () => {
    setLoading(true);
    setErrorMessage(null);
    try {
      const response = await fetch('/api/hotspots/v2/latest?limit=10');
      if (response.ok) {
        const data = await response.json();
        setAllData(data);
      } else {
        setErrorMessage('热点汇总数据加载失败，请稍后重试');
      }
    } catch (error) {
      console.error('加载全部数据失败:', error);
      setErrorMessage('热点汇总数据加载失败，请稍后重试');
    } finally {
      setLoading(false);
    }
  };

  const handleSync = async (source?: string) => {
    if (!isAdmin) return;

    setSyncing(true);
    setSyncResults({});
    setErrorMessage(null);
    try {
      const url = source
        ? `/api/hotspots/v2/sync?source=${source}`
        : '/api/hotspots/v2/sync';
      const response = await fetch(url, {
        method: 'POST',
        headers: await getAuthHeaders(),
      });
      if (response.ok) {
        const data = await response.json();
        setSyncResults(data.results || {});
        // 重新加载数据
        if (source) {
          await loadSourceData(source);
        } else {
          await loadAllData();
        }
      } else if (response.status === 401 || response.status === 403) {
        setErrorMessage('只有管理员可以同步热点数据');
      } else {
        setErrorMessage('热点同步失败，请稍后重试');
      }
    } catch (error) {
      console.error('同步失败:', error);
      setErrorMessage('热点同步失败，请稍后重试');
    } finally {
      setSyncing(false);
    }
  };

  const handleClearCache = async (source?: string) => {
    if (!isAdmin) return;
    setErrorMessage(null);

    try {
      const url = source
        ? `/api/hotspots/v2/cache?source=${source}`
        : '/api/hotspots/v2/cache';
      const response = await fetch(url, {
        method: 'DELETE',
        headers: await getAuthHeaders(),
      });
      if (!response.ok) {
        setErrorMessage(response.status === 401 || response.status === 403
          ? '只有管理员可以清除热点缓存'
          : '清除缓存失败，请稍后重试')
        return;
      }
      if (source) {
        await loadSourceData(source);
      }
    } catch (error) {
      console.error('清除缓存失败:', error);
      setErrorMessage('清除缓存失败，请稍后重试');
    }
  };

  const getRankChangeBadge = (change: number) => {
    if (change > 0) {
      return <Badge variant="success">↑ {change}</Badge>;
    } else if (change < 0) {
      return <Badge variant="error">↓ {Math.abs(change)}</Badge>;
    }
    return <Badge variant="default">-</Badge>;
  };

  return (
    <MainLayout>
      <div className="max-w-[1376px] mx-auto">
        {/* 页面标题 */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-3">
            <span className="text-[32px]">🔥</span>
            <div>
              <h1 className="font-heading text-[32px] font-semibold text-text-primary">
                热点中心
              </h1>
              <p className="font-body text-base text-text-secondary mt-1">
                聚合 11 个平台的实时热点，方便你从趋势里快速提炼选题。
              </p>
            </div>
          </div>
          <div className="flex gap-2">
            {/* 自动刷新开关 */}
            <Button
              icon={autoRefresh ? <Pause size={18} /> : <Play size={18} />}
              variant={autoRefresh ? 'primary' : 'secondary'}
              size="md"
              onClick={() => setAutoRefresh(!autoRefresh)}
            >
              {autoRefresh ? `${Math.floor(countdown / 60)}:${String(countdown % 60).padStart(2, '0')}` : '已暂停'}
            </Button>
            {isAdmin && (
              <>
                <Button
                  icon={<RefreshCw size={18} className={syncing ? 'animate-spin' : ''} />}
                  variant="secondary"
                  size="md"
                  onClick={() => handleSync()}
                  disabled={syncing}
                >
                  {syncing ? '同步中...' : '同步全部'}
                </Button>
                <Button
                  icon={<Database size={18} />}
                  variant="secondary"
                  size="md"
                  onClick={() => handleClearCache()}
                >
                  清除缓存
                </Button>
              </>
            )}
          </div>
        </div>

        {errorMessage && (
          <Card padding="md" className="mb-6 border border-red-200 bg-red-50">
            <p className="text-sm font-medium text-red-700">{errorMessage}</p>
          </Card>
        )}

        <Card padding="md" className="mb-6">
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div>
              <h2 className="font-heading text-lg font-semibold text-text-primary">热点资讯分区</h2>
              <p className="text-sm text-text-secondary mt-1">
                热点中心看榜单，新闻资讯看专题源，全网热点适合快速扫灵感。
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Link
                href="/hotspots"
                className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white"
              >
                <TrendingUp size={16} />
                热点中心
              </Link>
              <Link
                href="/news"
                className="inline-flex items-center gap-2 rounded-lg border border-border bg-white px-4 py-2 text-sm font-semibold text-text-primary hover:border-primary"
              >
                <Newspaper size={16} />
                新闻资讯
              </Link>
              <Link
                href="/inspiration"
                className="inline-flex items-center gap-2 rounded-lg border border-border bg-white px-4 py-2 text-sm font-semibold text-text-primary hover:border-primary"
              >
                <Lightbulb size={16} />
                全网热点
              </Link>
            </div>
          </div>
        </Card>

        {/* 数据源状态 */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
          <Card padding="md">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                <TrendingUp className="text-primary" size={20} />
              </div>
              <div>
                <p className="text-sm text-text-secondary">数据源</p>
                <p className="text-xl font-semibold text-text-primary">{sources.length} 个平台</p>
              </div>
            </div>
          </Card>
          <Card padding="md">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-success/10 flex items-center justify-center">
                <Database className="text-success" size={20} />
              </div>
              <div>
                <p className="text-sm text-text-secondary">自动刷新</p>
                <p className="text-xl font-semibold text-success">{autoRefresh ? '已开启' : '已暂停'}</p>
              </div>
            </div>
          </Card>
          <Card padding="md">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-secondary/10 flex items-center justify-center">
                <Clock className="text-secondary" size={20} />
              </div>
              <div>
                <p className="text-sm text-text-secondary">最后更新</p>
                <p className="text-sm font-semibold text-text-primary">
                  {sourceData?.updated_at ? new Date(sourceData.updated_at).toLocaleString('zh-CN') : '-'}
                </p>
              </div>
            </div>
          </Card>
        </div>

        {/* 平台选择 */}
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
              {source.icon || '📰'} {source.name}
            </button>
          ))}
        </div>

        {/* 同步结果 */}
        {Object.keys(syncResults).length > 0 && (
          <Card padding="md" className="mb-6 bg-success/5 border-success/20">
            <h3 className="font-semibold text-success mb-2">同步结果</h3>
            <div className="flex flex-wrap gap-3">
              {Object.entries(syncResults).map(([src, result]) => (
                <div key={src} className="text-sm">
                  <span className="font-medium">{src}:</span>{' '}
                  <span className={result.success ? 'text-success' : 'text-error'}>
                    {result.success ? `新增 ${result.created}, 更新 ${result.updated}` : '失败'}
                  </span>
                </div>
              ))}
            </div>
          </Card>
        )}

        {/* 热点列表 */}
        {loading ? (
          <Card padding="md">
            <div className="flex flex-col items-center justify-center py-10">
              <Loader2 className="animate-spin text-primary mb-3" size={40} />
              <p className="text-text-secondary text-sm">加载热点中...</p>
            </div>
          </Card>
        ) : !sourceData || sourceData.items.length === 0 ? (
          <Card padding="md">
            <div className="text-center py-10">
              <div className="text-5xl mb-3">📭</div>
              <h3 className="font-heading text-lg font-semibold text-text-primary mb-2">
                暂无热点数据
              </h3>
              <p className="font-body text-text-secondary text-sm mb-3">
                {isAdmin ? '点击同步按钮更新当前来源的热点数据' : '当前暂无可展示的热点数据'}
              </p>
              {isAdmin && (
                <Button variant="primary" size="sm" onClick={() => handleSync(currentSource)}>
                  同步数据
                </Button>
              )}
            </div>
          </Card>
        ) : (
          <Card padding="sm">
            <div className="flex items-center justify-between px-3 py-2 border-b border-border">
              <span className="text-sm text-text-secondary">
                共 {sourceData.count} 条热点
              </span>
              {isAdmin && (
                <Button
                  variant="text"
                  size="sm"
                  onClick={() => handleSync(currentSource)}
                  disabled={syncing}
                >
                  <RefreshCw size={14} className={syncing ? 'animate-spin' : ''} />
                  <span className="ml-1">同步</span>
                </Button>
              )}
            </div>
            {sourceData.items.map((item, index) => (
              <div
                key={item.id}
                className={`flex items-center gap-3 p-3 hover:bg-bg transition-colors ${
                  index < sourceData.items.length - 1 ? 'border-b border-border' : ''
                }`}
              >
                {/* 排名 */}
                <div
                  className={`w-8 h-8 rounded-lg flex items-center justify-center font-body text-sm font-semibold flex-shrink-0 ${
                    item.rank <= 3
                      ? 'bg-primary text-white'
                      : 'bg-white border-2 border-border text-text-secondary'
                  }`}
                >
                  {item.rank}
                </div>

                {/* 新增标记 */}
                {item.is_new && (
                  <Badge variant="success" className="flex-shrink-0">NEW</Badge>
                )}

                {/* 排名变化 */}
                {item.rank_change !== 0 && (
                  <div className="flex-shrink-0">
                    {getRankChangeBadge(item.rank_change)}
                  </div>
                )}

                {/* 标题和描述 */}
                <div className="flex-grow min-w-0">
                  <h3 className="font-body text-sm font-semibold text-text-primary mb-1 line-clamp-1">
                    {item.title}
                  </h3>
                  {item.description && (
                    <p className="text-xs text-text-secondary line-clamp-1">
                      {item.description}
                    </p>
                  )}
                </div>

                {/* 热度值 */}
                {item.hot_value && (
                  <div className="flex-shrink-0 text-right">
                    <span className="text-xs text-text-secondary">热度</span>
                    <p className="text-sm font-semibold text-primary">
                      {item.hot_value >= 10000 ? `${(item.hot_value / 10000).toFixed(1)}万` : item.hot_value}
                    </p>
                  </div>
                )}

                {/* 链接 */}
                {item.url && (
                  <a
                    href={item.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-primary hover:text-primary/80 flex-shrink-0"
                  >
                    <ExternalLink size={16} />
                  </a>
                )}
              </div>
            ))}
          </Card>
        )}

      </div>
    </MainLayout>
  );
}
