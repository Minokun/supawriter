'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import {
  FileText,
  Type,
  Calendar,
  Zap,
  TrendingUp,
  PieChart,
  Target,
  Cpu,
  Loader2,
  Crown,
  Lock,
} from 'lucide-react';
import MainLayout from '@/components/layout/MainLayout';
import Card from '@/components/ui/Card';
import Button from '@/components/ui/Button';
import { useToast } from '@/components/ui/ToastContainer';
import {
  dashboardApi,
  DashboardStats,
  MembershipTier,
} from '@/types/api';
import { useAuth } from '@/hooks/useAuth';

// 统计卡片组件
interface StatCardProps {
  title: string;
  value: string | number;
  icon: React.ReactNode;
  subtitle?: string;
  trend?: {
    value: number;
    isPositive: boolean;
  };
  color?: 'primary' | 'success' | 'warning' | 'info';
}

function StatCard({ title, value, icon, subtitle, trend, color = 'primary' }: StatCardProps) {
  const colorClasses = {
    primary: 'bg-primary/10 text-primary',
    success: 'bg-green-100 text-green-600',
    warning: 'bg-amber-100 text-amber-600',
    info: 'bg-blue-100 text-blue-600',
  };

  return (
    <Card padding="lg" className="h-full">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-text-secondary mb-1">{title}</p>
          <p className="text-3xl font-bold text-text-primary">{value}</p>
          {subtitle && <p className="text-xs text-text-tertiary mt-1">{subtitle}</p>}
          {trend && (
            <div className={`flex items-center gap-1 mt-2 text-sm ${trend.isPositive ? 'text-green-600' : 'text-red-500'}`}>
              <TrendingUp size={14} className={trend.isPositive ? '' : 'rotate-180'} />
              <span>{trend.value}%</span>
            </div>
          )}
        </div>
        <div className={`p-3 rounded-xl ${colorClasses[color]}`}>
          {icon}
        </div>
      </div>
    </Card>
  );
}

// 评分趋势图（简化版）
function ScoreChart({ data }: { data: { date: string; score: number }[] }) {
  if (!data || data.length === 0) return null;

  const maxScore = Math.max(...data.map(d => d.score), 100);
  const minScore = Math.min(...data.map(d => d.score), 0);
  const range = maxScore - minScore || 1;

  return (
    <div className="h-48 flex items-end gap-2">
      {data.slice(-10).map((item, index) => {
        const height = ((item.score - minScore) / range) * 100;
        return (
          <div key={index} className="flex-1 flex flex-col items-center gap-1">
            <div
              className="w-full bg-primary/20 rounded-t-lg relative group cursor-pointer"
              style={{ height: `${Math.max(height, 10)}%` }}
            >
              <div
                className="absolute bottom-0 left-0 right-0 bg-primary rounded-t-lg transition-all group-hover:bg-primary/80"
                style={{ height: '100%' }}
              />
              {/* Tooltip */}
              <div className="absolute -top-8 left-1/2 -translate-x-1/2 bg-text-primary text-white text-xs px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap z-10">
                {item.score}分
              </div>
            </div>
            <span className="text-xs text-text-tertiary">
              {new Date(item.date).getMonth() + 1}/{new Date(item.date).getDate()}
            </span>
          </div>
        );
      })}
    </div>
  );
}

// 平台分布饼图（简化版）
function PlatformChart({ data }: { data: Record<string, number> }) {
  if (!data || Object.keys(data).length === 0) return null;

  const total = Object.values(data).reduce((sum, val) => sum + val, 0);
  const platforms = Object.entries(data).sort((a, b) => b[1] - a[1]);

  const colors: Record<string, string> = {
    wechat: '#07C160',
    zhihu: '#0084FF',
    xiaohongshu: '#FF2442',
    toutiao: '#ED4040',
    weibo: '#E6162D',
    default: '#6366F1',
  };

  return (
    <div className="flex items-center gap-6">
      <div className="relative w-32 h-32">
        <svg viewBox="0 0 100 100" className="transform -rotate-90">
          {platforms.reduce(
            (acc, [platform, count], index) => {
              const percentage = (count / total) * 100;
              const dashArray = `${percentage} ${100 - percentage}`;
              const offset = 100 - acc.cumulative;
              acc.cumulative += percentage;

              acc.elements.push(
                <circle
                  key={platform}
                  cx="50"
                  cy="50"
                  r="40"
                  fill="none"
                  stroke={colors[platform] || colors.default}
                  strokeWidth="20"
                  strokeDasharray={dashArray}
                  strokeDashoffset={offset}
                  className="transition-all hover:opacity-80"
                />
              );
              return acc;
            },
            { elements: [] as React.ReactNode[], cumulative: 0 }
          ).elements}
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-2xl font-bold text-text-primary">{total}</span>
        </div>
      </div>
      <div className="flex-1 space-y-2">
        {platforms.map(([platform, count]) => (
          <div key={platform} className="flex items-center justify-between text-sm">
            <div className="flex items-center gap-2">
              <div
                className="w-3 h-3 rounded-full"
                style={{ backgroundColor: colors[platform] || colors.default }}
              />
              <span className="text-text-secondary capitalize">{platform}</span>
            </div>
            <span className="font-medium text-text-primary">{count}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// 模型使用分布柱状图
function ModelUsageChart({ data }: { data: Record<string, number> }) {
  if (!data || Object.keys(data).length === 0) return null;

  const maxValue = Math.max(...Object.values(data));
  const models = Object.entries(data).sort((a, b) => b[1] - a[1]);

  return (
    <div className="space-y-3">
      {models.map(([model, count]) => {
        const percentage = maxValue > 0 ? (count / maxValue) * 100 : 0;
        return (
          <div key={model} className="space-y-1">
            <div className="flex items-center justify-between text-sm">
              <span className="text-text-secondary">{model}</span>
              <span className="font-medium text-text-primary">{count}次</span>
            </div>
            <div className="h-2 bg-bg rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-primary to-purple-500 rounded-full transition-all"
                style={{ width: `${percentage}%` }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}

// 升级提示卡片
function UpgradeCard({ tier, feature }: { tier: MembershipTier; feature: string }) {
  const router = useRouter();

  return (
    <div className="relative overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-br from-primary/5 to-purple-500/5" />
      <Card padding="lg" className="relative border-dashed border-2 border-primary/30">
        <div className="flex flex-col items-center text-center py-6">
          <div className="w-12 h-12 bg-primary/10 rounded-full flex items-center justify-center mb-3">
            <Lock className="text-primary" size={24} />
          </div>
          <h3 className="font-semibold text-text-primary mb-1">{feature}</h3>
          <p className="text-sm text-text-secondary mb-4">
            升级至 {tier === 'pro' ? 'Pro' : 'Ultra'} 会员解锁此功能
          </p>
          <Button variant="primary" size="sm" onClick={() => router.push('/pricing')}>
            <Crown size={16} className="mr-1" />
            升级会员
          </Button>
        </div>
      </Card>
    </div>
  );
}

export default function DashboardPage() {
  const router = useRouter();
  const { status, isAuthenticated, membershipTier, profileResolved } = useAuth();
  const { showError } = useToast();
  const signInHref = '/auth/signin?callbackUrl=%2Fdashboard';

  const authResolved = status !== 'loading';
  const tierResolved = !isAuthenticated || profileResolved;

  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);

  const loadStats = useCallback(async () => {
    if (!isAuthenticated || !tierResolved) return;
    setLoading(true);
    try {
      const response = await dashboardApi.getStats();
      setStats(response);
    } catch (error) {
      console.error('Failed to load dashboard stats:', error);
      showError('加载统计数据失败');
    } finally {
      setLoading(false);
    }
  }, [isAuthenticated, showError, tierResolved]);

  useEffect(() => {
    if (status === 'authenticated' && tierResolved) {
      loadStats();
    } else if (status === 'unauthenticated') {
      setStats(null);
      setLoading(false);
    } else {
      setLoading(true);
    }
  }, [status, loadStats, tierResolved]);

  useEffect(() => {
    if (status !== 'unauthenticated') {
      return;
    }
    router.replace(signInHref);
  }, [router, signInHref, status]);

  // 判断是否是 Pro 或 Ultra
  const isPro = membershipTier === 'pro' || membershipTier === 'ultra' || membershipTier === 'superuser';
  const isUltra = membershipTier === 'ultra' || membershipTier === 'superuser';

  // 格式化数字
  const formatNumber = (num: number) => {
    if (num >= 10000) return (num / 10000).toFixed(1) + '万';
    return num.toLocaleString();
  };

  if (!authResolved || !tierResolved || loading) {
    return (
      <MainLayout>
        <div className="max-w-[1376px] mx-auto">
          <div className="flex items-center justify-center py-12">
            <Loader2 className="animate-spin text-primary mr-4" size={48} />
            <p className="text-text-secondary text-lg">加载中...</p>
          </div>
        </div>
      </MainLayout>
    );
  }

  if (status === 'unauthenticated') {
    return (
      <MainLayout>
        <div className="max-w-[1376px] mx-auto">
          <div className="flex flex-col items-center justify-center py-12">
            <Loader2 className="animate-spin text-primary mb-4" size={40} />
            <p className="text-text-secondary text-lg">正在跳转到登录...</p>
          </div>
        </div>
      </MainLayout>
    );
  }

  const baseStats = stats;
  const proStats = stats;
  const ultraStats = stats;

  return (
    <MainLayout>
      <div className="max-w-[1376px] mx-auto">
        {/* 页面标题 */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-3">
            <span className="text-[32px]">📊</span>
            <div>
              <h1 className="font-heading text-[32px] font-semibold text-text-primary">
                数据看板
              </h1>
              <p className="font-body text-base text-text-secondary mt-1">
                查看您的创作统计数据和趋势分析
              </p>
            </div>
          </div>
          <Button variant="secondary" size="sm" onClick={loadStats}>
            刷新数据
          </Button>
        </div>

        {/* 基础统计 - Free 及以上 */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <StatCard
            title="总创作数"
            value={formatNumber(baseStats?.total_articles || 0)}
            icon={<FileText size={24} />}
            color="primary"
          />
          <StatCard
            title="累计字数"
            value={formatNumber(baseStats?.total_words || 0)}
            icon={<Type size={24} />}
            color="success"
          />
          <StatCard
            title="本月生成"
            value={`${baseStats?.monthly_articles || 0} / ${baseStats?.quota_total || 0}`}
            icon={<Calendar size={24} />}
            subtitle={`剩余 ${(baseStats?.quota_total || 0) - (baseStats?.quota_used || 0)} 篇`}
            color="warning"
          />
          <StatCard
            title="配额使用"
            value={`${Math.round(((baseStats?.quota_used || 0) / (baseStats?.quota_total || 1)) * 100)}%`}
            icon={<Zap size={24} />}
            subtitle={`${baseStats?.quota_used || 0} / ${baseStats?.quota_total || 0}`}
            color="info"
          />
        </div>

        {/* Pro 功能 */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          {isPro ? (
            <>
              {/* 评分趋势 */}
              <Card padding="lg">
                <div className="flex items-center gap-2 mb-4">
                  <TrendingUp className="text-primary" size={24} />
                  <h2 className="font-heading text-xl font-semibold text-text-primary">
                    评分趋势
                  </h2>
                </div>
                {proStats?.score_history && proStats.score_history.length > 0 ? (
                  <ScoreChart data={proStats.score_history} />
                ) : (
                  <div className="h-48 flex items-center justify-center text-text-secondary">
                    <p>暂无评分数据，生成文章并评分后查看趋势</p>
                  </div>
                )}
                {proStats?.avg_score !== undefined && (
                  <div className="mt-4 pt-4 border-t border-border flex items-center justify-between">
                    <span className="text-text-secondary">平均评分</span>
                    <span className="text-2xl font-bold text-primary">{proStats.avg_score.toFixed(1)}</span>
                  </div>
                )}
              </Card>

              {/* 平台分布 */}
              <Card padding="lg">
                <div className="flex items-center gap-2 mb-4">
                  <PieChart className="text-primary" size={24} />
                  <h2 className="font-heading text-xl font-semibold text-text-primary">
                    平台分布
                  </h2>
                </div>
                {proStats?.platform_stats && Object.keys(proStats.platform_stats).length > 0 ? (
                  <PlatformChart data={proStats.platform_stats} />
                ) : (
                  <div className="h-48 flex items-center justify-center text-text-secondary">
                    <p>暂无平台转换数据</p>
                  </div>
                )}
              </Card>
            </>
          ) : (
            <>
              <UpgradeCard tier="pro" feature="评分趋势图" />
              <UpgradeCard tier="pro" feature="平台分布图" />
            </>
          )}
        </div>

        {/* Ultra 功能 */}
        {isUltra ? (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* 热点匹配统计 */}
            <Card padding="lg">
              <div className="flex items-center gap-2 mb-4">
                <Target className="text-primary" size={24} />
                <h2 className="font-heading text-xl font-semibold text-text-primary">
                  热点匹配
                </h2>
              </div>
              <div className="text-center py-6">
                <p className="text-5xl font-bold text-primary mb-2">
                  {ultraStats?.hotspot_matches || 0}
                </p>
                <p className="text-text-secondary">累计匹配热点数</p>
              </div>
            </Card>

            {/* 关键词命中率 */}
            <Card padding="lg">
              <div className="flex items-center gap-2 mb-4">
                <Target className="text-primary" size={24} />
                <h2 className="font-heading text-xl font-semibold text-text-primary">
                  关键词命中率
                </h2>
              </div>
              <div className="text-center py-6">
                <p className="text-5xl font-bold text-primary mb-2">
                  {((ultraStats?.keyword_hit_rate || 0) * 100).toFixed(1)}%
                </p>
                <p className="text-text-secondary">关键词匹配成功率</p>
              </div>
            </Card>

            {/* 模型使用分布 */}
            <Card padding="lg">
              <div className="flex items-center gap-2 mb-4">
                <Cpu className="text-primary" size={24} />
                <h2 className="font-heading text-xl font-semibold text-text-primary">
                  模型使用分布
                </h2>
              </div>
              {ultraStats?.model_usage && Object.keys(ultraStats.model_usage).length > 0 ? (
                <ModelUsageChart data={ultraStats.model_usage} />
              ) : (
                <div className="h-32 flex items-center justify-center text-text-secondary">
                  <p>暂无模型使用数据</p>
                </div>
              )}
            </Card>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <UpgradeCard tier="ultra" feature="热点匹配统计" />
            <UpgradeCard tier="ultra" feature="关键词命中率" />
            <UpgradeCard tier="ultra" feature="模型使用分布" />
          </div>
        )}
      </div>
    </MainLayout>
  );
}
