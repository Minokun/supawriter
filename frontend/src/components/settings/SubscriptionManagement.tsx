'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';
import Card from '@/components/ui/Card';
import Button from '@/components/ui/Button';
import Badge from '@/components/ui/Badge';
import { useToast } from '@/components/ui/ToastContainer';
import { Loader2, Crown, Calendar, ArrowRight, Sparkles } from 'lucide-react';
import { subscriptionApi, quotaApi, type SubscriptionResponse, type QuotaInfo } from '@/lib/api/billing';

export function SubscriptionManagement() {
  const router = useRouter();
  const { membershipTier, isAuthenticated } = useAuth();
  const { showSuccess, showError } = useToast();

  const [subscription, setSubscription] = useState<SubscriptionResponse | null>(null);
  const [quotaInfo, setQuotaInfo] = useState<QuotaInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [cancelling, setCancelling] = useState(false);

  useEffect(() => {
    if (!isAuthenticated) {
      setLoading(false);
      return;
    }
    loadData();
  }, [isAuthenticated]);

  const loadData = async () => {
    try {
      setLoading(true);
      const [subRes, quotaRes] = await Promise.all([
        subscriptionApi.get().catch(() => null),
        quotaApi.get().catch(() => null),
      ]);
      setSubscription(subRes);
      setQuotaInfo(quotaRes);
    } catch (error) {
      console.error('Failed to load subscription data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCancelSubscription = async () => {
    if (!confirm('确定要取消订阅吗？取消后当前周期内权益保留，周期结束后将不再续费。')) {
      return;
    }

    try {
      setCancelling(true);
      await subscriptionApi.cancel();
      showSuccess('订阅已取消，当前周期结束后将不再续费');
      await loadData();
    } catch (error: any) {
      showError(error.message || '取消失败，请重试');
    } finally {
      setCancelling(false);
    }
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('zh-CN', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  // Use explicit feature tier from the subscription API as source of truth.
  const effectivePlan = subscription?.feature_tier ?? membershipTier ?? 'free';

  const getPlanName = (plan: string) => {
    const names: Record<string, string> = {
      free: 'Free',
      pro: 'Pro',
      ultra: 'Ultra',
      superuser: 'Superuser',
    };
    return names[plan] || plan;
  };

  if (loading) {
    return (
      <Card padding="xl">
        <div className="flex items-center justify-center py-12">
          <Loader2 className="animate-spin text-primary mr-4" size={32} />
          <p className="text-text-secondary">加载中...</p>
        </div>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <Card padding="xl">
        <div className="flex items-center gap-2 mb-6">
          <Crown className="text-primary" size={24} />
          <h2 className="font-heading text-xl font-semibold text-text-primary">
            当前方案
          </h2>
        </div>

        <div className="bg-gradient-to-r from-primary/10 to-primary/5 rounded-xl p-6 mb-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <div className="flex items-center gap-3 mb-2">
                <span className="font-heading text-2xl font-bold text-text-primary">
                  {getPlanName(effectivePlan)} 会员
                </span>
                {subscription?.has_active_subscription && subscription.status === 'cancelled' && (
                  <Badge variant="warning">已取消</Badge>
                )}
                {subscription?.has_active_subscription && subscription.status === 'active' && (
                  <Badge variant="success">生效中</Badge>
                )}
                {!subscription?.has_active_subscription && effectivePlan !== 'free' && (
                  <Badge variant="default">无活跃订阅</Badge>
                )}
              </div>
              <p className="text-sm text-text-secondary">
                {effectivePlan === 'free'
                  ? '免费版，享受基础功能'
                  : subscription?.has_active_subscription
                    ? '已开通付费订阅，享受更多高级功能'
                    : '当前功能等级由账号权限决定，暂未检测到活跃付费订阅'}
              </p>
            </div>
            <div className="text-right">
              {subscription?.has_active_subscription && subscription?.current_period_end && (
                <div className="flex items-center gap-2 text-sm text-text-secondary">
                  <Calendar size={16} />
                  <span>
                    {subscription.status === 'cancelled'
                      ? `有效期至 ${formatDate(subscription.current_period_end)}`
                      : `下次续费：${formatDate(subscription.current_period_end)}`
                    }
                  </span>
                </div>
              )}
            </div>
          </div>

          {subscription?.has_active_subscription && subscription && (
            <div className="flex items-center gap-2 text-sm text-text-secondary">
              <span>周期类型：</span>
              <Badge variant="default" className="text-xs">
                {subscription.current_period === 'monthly' ? '月付' : subscription.current_period === 'quarterly' ? '季付' : '年付'}
              </Badge>
              {subscription.auto_renew && (
                <span className="ml-2 text-green-600">自动续费已开启</span>
              )}
            </div>
          )}
        </div>

        {quotaInfo && (
          <div className="space-y-4 mb-6">
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-text-primary font-medium">本月方案配额</span>
                <span className="text-text-secondary text-sm">
                  {quotaInfo.plan_used} / {quotaInfo.plan_quota} 次
                </span>
              </div>
              <div className="w-full bg-bg rounded-full h-3">
                <div
                  className={`rounded-full h-3 transition-all duration-300 ${(quotaInfo.plan_used / quotaInfo.plan_quota) > 0.8 ? 'bg-amber-500' : 'bg-primary'}`}
                  style={{ width: `${Math.min((quotaInfo.plan_used / quotaInfo.plan_quota) * 100, 100)}%` }}
                />
              </div>
            </div>

            {quotaInfo.pack_quota > 0 && (
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-text-primary font-medium">额度包剩余</span>
                  <span className="text-text-secondary text-sm">
                    {quotaInfo.pack_remaining} / {quotaInfo.pack_quota} 次
                  </span>
                </div>
                <div className="w-full bg-bg rounded-full h-3">
                  <div
                    className="bg-green-500 rounded-full h-3 transition-all duration-300"
                    style={{ width: `${Math.min((quotaInfo.pack_remaining / quotaInfo.pack_quota) * 100, 100)}%` }}
                  />
                </div>
              </div>
            )}

            <div className="pt-4 border-t border-border">
              <div className="flex items-center justify-between">
                <span className="text-text-primary font-medium">总计剩余配额</span>
                <span className="font-heading text-3xl font-bold text-primary">
                  {quotaInfo.total_remaining} 次
                </span>
              </div>
            </div>
          </div>
        )}

        <div className="flex gap-3">
          <Button
            variant="primary"
            size="lg"
            onClick={() => router.push('/pricing')}
            className="flex-1"
          >
            查看定价方案
            <ArrowRight className="ml-2" size={18} />
          </Button>
          {subscription?.has_active_subscription && subscription?.status === 'active' && (
            <Button
              variant="secondary"
              size="lg"
              onClick={handleCancelSubscription}
              disabled={cancelling}
              className="border-red-300 text-red-600 hover:bg-red-50"
            >
              {cancelling ? (
                <>
                  <Loader2 className="animate-spin mr-2" size={16} />
                  取消中...
                </>
              ) : (
                '取消订阅'
              )}
            </Button>
          )}
        </div>
      </Card>

      <Card padding="lg">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="font-heading text-lg font-semibold text-text-primary mb-1">
              额度不足？购买额度包
            </h3>
            <p className="text-sm text-text-secondary">
              额度包购买后永久有效（1年内），不自动续费
            </p>
          </div>
          <Button variant="primary" onClick={() => router.push('/pricing')}>
            查看额度包
          </Button>
        </div>
      </Card>

      <Card padding="xl">
        <div className="flex items-center gap-2 mb-6">
          <Sparkles className="text-primary" size={24} />
          <h2 className="font-heading text-xl font-semibold text-text-primary">
            方案权益对比
          </h2>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-border">
                <th className="text-left py-3 px-4 font-body text-sm font-semibold text-text-primary">功能</th>
                <th className="text-center py-3 px-4 font-body text-sm font-semibold text-text-primary">Free</th>
                <th className="text-center py-3 px-4 font-body text-sm font-semibold text-text-primary">Pro</th>
                <th className="text-center py-3 px-4 font-body text-sm font-semibold text-text-primary">Ultra</th>
              </tr>
            </thead>
            <tbody>
              {[
                { feature: '每月配额', free: '5次', pro: '20次', ultra: '60次' },
                { feature: '基础模型', free: '✅', pro: '✅', ultra: '✅' },
                { feature: '中级模型', free: '❌', pro: '✅', ultra: '✅' },
                { feature: '顶级模型', free: '❌', pro: '❌', ultra: '✅' },
                { feature: 'SEO优化', free: '❌', pro: '✅', ultra: '✅' },
                { feature: '多平台转换', free: '❌', pro: '✅', ultra: '✅' },
                { feature: '热点预警', free: '❌', pro: '✅', ultra: '✅' },
                { feature: '去水印', free: '❌', pro: '✅', ultra: '✅' },
                { feature: '数据看板', free: '基础', pro: '+图表', ultra: '完整' },
                { feature: '批量生成', free: '❌', pro: '❌', ultra: '✅' },
                { feature: '写作 Agent', free: '❌', pro: '❌', ultra: '✅' },
              ].map((item, index) => (
                <tr key={index} className="border-b border-border last:border-0">
                  <td className="py-3 px-4 text-sm text-text-primary">{item.feature}</td>
                  <td className="py-3 px-4 text-center text-sm text-text-secondary">{item.free}</td>
                  <td className={`py-3 px-4 text-center text-sm ${effectivePlan === 'pro' ? 'text-primary font-semibold' : 'text-text-secondary'}`}>
                    {item.pro}
                  </td>
                  <td className={`py-3 px-4 text-center text-sm ${effectivePlan === 'ultra' ? 'text-primary font-semibold' : 'text-text-secondary'}`}>
                    {item.ultra}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
