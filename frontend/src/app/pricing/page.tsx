'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Check, Loader2, Sparkles, Crown, Gift, Shield, Calendar, ArrowRight } from 'lucide-react';
import MainLayout from '@/components/layout/MainLayout';
import Card from '@/components/ui/Card';
import Button from '@/components/ui/Button';
import { useToast } from '@/components/ui/ToastContainer';
import { useSharedAuth } from '@/contexts/AuthContext';
import {
  pricingApi,
  subscriptionApi,
  quotaApi,
  type PricingPlan,
  type QuotaPack,
  type QuotaInfo,
  type SubscriptionResponse,
} from '@/lib/api/billing';

// ===== 常量 =====

const TIER_ORDER: Record<string, number> = { free: 0, pro: 1, ultra: 2, superuser: 3 };

const PLAN_NAMES: Record<string, string> = { free: 'Free', pro: 'Pro', ultra: 'Ultra', superuser: 'Super' };
const PERIOD_NAMES: Record<string, string> = { monthly: '月付', quarterly: '季付', yearly: '年付' };
const PERIOD_SUFFIX: Record<string, string> = { monthly: '/月', quarterly: '/季', yearly: '/年' };

const FEATURES: Record<string, string[]> = {
  free: ['基础模型访问', '5篇文章/月', '历史记录保存7天', '社区基础功能'],
  pro: ['中级模型访问', '20篇文章/月', 'SEO优化功能', '多平台转换', '热点预警', '去水印', '历史记录永久保存', '数据看板（含图表）'],
  ultra: ['全部模型访问（含顶级）', '60篇文章/月', '所有Pro功能', '批量生成', '写作 Agent', '数据看板（完整版）', '优先客服支持', 'API接口访问'],
  superuser: ['全部模型访问', '无限文章生成', '所有功能解锁', '系统管理权限', '批量生成', '写作 Agent', '完整数据看板', 'API接口访问'],
};

const FAQS = [
  { q: '不同会员等级有什么区别？', a: 'Free用户每月5篇，基础模型；Pro用户每月20篇，中级模型，含SEO优化、多平台转换等高级功能；Ultra用户每月60篇，全部模型，还享有批量生成和写作 Agent。' },
  { q: '可以随时取消订阅吗？', a: '可以。取消后当前计费周期内权益保留，周期结束后不再续费。' },
  { q: '额度包和订阅有什么区别？', a: '订阅按月/季/年付费，周期结束后配额重置；额度包按需购买，购买后1年内有效，不自动续费。' },
  { q: '如何支付？', a: '目前支持模拟支付，后续将接入微信和支付宝。' },
  { q: '会员可以降级吗？', a: '暂不支持降级。当前订阅到期后不再续费，账户会自动恢复为Free用户。如需帮助，请联系客服。' },
];

// 与后端 PricingService 对齐的 fallback
const FALLBACK_PLANS: PricingPlan[] = [
  { id: 'free', name: 'Free', prices: { monthly: 0, quarterly: 0, yearly: 0 }, features: FEATURES.free, quota: 5 },
  { id: 'pro', name: 'Pro', prices: { monthly: 2990, quarterly: 7990, yearly: 29900 }, features: FEATURES.pro, quota: 20, popular: true },
  { id: 'ultra', name: 'Ultra', prices: { monthly: 5990, quarterly: 14900, yearly: 49900 }, features: FEATURES.ultra, quota: 60 },
];

const FALLBACK_PACKS: QuotaPack[] = [
  { id: 'pack_10', quota: 10, price: 1990 },
  { id: 'pack_50', quota: 50, price: 7990 },
];

// ===== 工具函数 =====

function formatPrice(cents: number) {
  const value = cents / 100;
  return Number.isInteger(value) ? String(value) : value.toFixed(1);
}

function formatDate(dateStr: string | null | undefined) {
  if (!dateStr) return '—';
  return new Date(dateStr).toLocaleDateString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric' });
}

function getUpgradablePlans(currentTier: string, allPlans: PricingPlan[]): PricingPlan[] {
  const order = TIER_ORDER[currentTier] ?? 0;
  return allPlans.filter((p) => (TIER_ORDER[p.id] ?? 0) > order);
}

// ===== 子组件 =====

function CurrentPlanCard({ sub, quota }: { sub: SubscriptionResponse | null; quota: QuotaInfo | null }) {
  const tier = sub?.feature_tier ?? 'free';
  const status = sub?.status ?? 'inactive';

  const statusLabel: Record<string, { text: string; color: string }> = {
    active: { text: '生效中', color: 'bg-green-100 text-green-700' },
    cancelled: { text: '已取消（到期后失效）', color: 'bg-amber-100 text-amber-700' },
    expired: { text: '已过期', color: 'bg-red-100 text-red-700' },
    inactive: { text: '无活跃订阅', color: 'bg-slate-100 text-slate-700' },
  };
  const isSuper = tier === 'superuser';
  const badge = tier === 'free'
    ? { text: '免费版', color: 'bg-slate-100 text-slate-700' }
    : isSuper
    ? { text: '系统管理员', color: 'bg-purple-100 text-purple-700' }
    : (statusLabel[status] ?? statusLabel.active);

  return (
    <Card padding="xl" className="bg-gradient-to-r from-primary/10 to-primary/5">
      <div className="flex items-center gap-2 mb-6">
        <Crown className="text-primary" size={24} />
        <h2 className="font-heading text-xl font-semibold text-text-primary">当前方案</h2>
      </div>

      <div className="flex flex-col md:flex-row gap-6">
        {/* 栏1：等级信息 */}
        <div className="md:w-[22%] md:border-r border-primary/10 md:pr-6">
          <div className="flex flex-col items-center md:items-start gap-2 mb-3">
            <span className="font-heading text-3xl font-bold text-text-primary">
              {PLAN_NAMES[tier] ?? tier}
            </span>
            <span className={`px-3 py-1 text-xs font-semibold rounded-full ${badge.color}`}>
              {badge.text}
            </span>
          </div>

          {sub?.has_active_subscription && sub?.current_period && tier !== 'free' && (
            <div className="space-y-1.5 text-sm text-text-secondary">
              <p>{PERIOD_NAMES[sub.current_period] ?? sub.current_period}</p>
              {sub.current_period_start && sub.current_period_end && (
                <div className="flex items-center gap-1.5">
                  <Calendar size={14} />
                  <span>{formatDate(sub.current_period_start)} ~ {formatDate(sub.current_period_end)}</span>
                </div>
              )}
              <p>{sub.auto_renew ? '自动续费已开启' : '不自动续费'}</p>
            </div>
          )}
          {tier === 'free' && (
            <p className="text-sm text-text-secondary">免费版，享受基础功能</p>
          )}
        </div>

        {/* 栏2：权益列表 */}
        <div className="md:w-[28%] md:border-r border-primary/10 md:px-6">
          <h3 className="text-sm font-medium text-text-primary mb-3">等级权益</h3>
          <div className="space-y-2">
            {(FEATURES[tier] ?? []).map((f, i) => (
              <div key={i} className="flex items-center gap-2">
                <div className="w-4 h-4 rounded-full bg-green-100 flex items-center justify-center flex-shrink-0">
                  <Check className="w-2.5 h-2.5 text-green-600" />
                </div>
                <span className="text-xs text-text-secondary">{f}</span>
              </div>
            ))}
          </div>
        </div>

        {/* 栏3：额度进度 */}
        {quota && (
          <div className="md:w-1/2 md:pl-6 space-y-3">
            {isSuper ? (
              <div className="flex flex-col items-center justify-center h-full py-4">
                <span className="font-heading text-3xl font-bold text-primary">∞ 无限制</span>
                <span className="text-sm text-text-secondary mt-2">管理员享有无限配额</span>
              </div>
            ) : (
            <>
            <div>
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm text-text-secondary">方案配额</span>
                <span className="text-sm text-text-secondary">
                  {quota.plan_used} / {quota.plan_quota} 次
                </span>
              </div>
              <div className="w-full bg-white/60 rounded-full h-2.5">
                <div
                  className={`h-2.5 rounded-full transition-all duration-300 ${quota.plan_used / quota.plan_quota > 0.8 ? 'bg-amber-500' : 'bg-primary'}`}
                  style={{ width: `${Math.min((quota.plan_used / Math.max(quota.plan_quota, 1)) * 100, 100)}%` }}
                />
              </div>
            </div>

            {quota.pack_remaining > 0 && (
              <div>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm text-text-secondary">额度包剩余</span>
                  <span className="text-sm text-text-secondary">{quota.pack_remaining} 次</span>
                </div>
                <div className="w-full bg-white/60 rounded-full h-2.5">
                  <div
                    className="bg-green-500 h-2.5 rounded-full transition-all duration-300"
                    style={{ width: `${Math.min((quota.pack_remaining / Math.max(quota.pack_quota, 1)) * 100, 100)}%` }}
                  />
                </div>
              </div>
            )}

            <div className="pt-3 border-t border-primary/10">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-text-primary">总计剩余</span>
                <span className="font-heading text-xl font-bold text-primary">{quota.total_remaining} 次</span>
              </div>
            </div>
            </>
            )}
          </div>
        )}
      </div>
    </Card>
  );
}

function UpgradeCard({
  plan,
  period,
  onPeriodChange,
  onUpgrade,
  upgrading,
  isCurrentPlan,
  isDowngrade,
}: {
  plan: PricingPlan;
  period: string;
  onPeriodChange: (p: string) => void;
  onUpgrade: (planId: string) => void;
  upgrading: string | null;
  isCurrentPlan?: boolean;
  isDowngrade?: boolean;
}) {
  const periods = ['monthly', 'quarterly', 'yearly'] as const;
  const savings = (p: string) => {
    if (p === 'monthly') return null;
    const months = p === 'quarterly' ? 3 : 12;
    const full = plan.prices.monthly * months;
    const current = plan.prices[p as keyof typeof plan.prices];
    if (full <= 0 || current >= full) return null;
    return Math.round((1 - current / full) * 100);
  };

  return (
    <Card
      padding="xl"
      className={`relative transition-all ${isCurrentPlan ? 'border-2 border-primary bg-primary/5' : plan.popular ? 'border-2 border-primary' : ''}`}
    >
      {isCurrentPlan && (
        <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-4 py-1 bg-gradient-to-r from-primary to-primary/80 text-white text-sm font-semibold rounded-full flex items-center gap-1 shadow-lg">
          <Check size={14} />
          当前方案
        </div>
      )}
      {!isCurrentPlan && plan.popular && (
        <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-4 py-1 bg-gradient-to-r from-primary to-primary/80 text-white text-sm font-semibold rounded-full flex items-center gap-1 shadow-lg">
          <Sparkles size={14} />
          最受欢迎
        </div>
      )}

      <div className="text-center mb-6">
        <h3 className="font-heading text-xl font-semibold text-text-primary mb-2">{plan.name}</h3>
        <div className="flex items-baseline justify-center gap-1">
          <span className="font-heading text-[48px] font-bold text-text-primary">
            ¥{formatPrice(plan.prices[period as keyof typeof plan.prices] ?? plan.prices.monthly)}
          </span>
          <span className="text-sm text-text-tertiary">{PERIOD_SUFFIX[period] ?? '/月'}</span>
        </div>
        <p className="mt-2 text-sm text-text-secondary">每月 {plan.quota} 篇文章</p>
      </div>

      {/* 周期选择 */}
      <div className="flex justify-center gap-2 mb-6">
        {periods.map((p) => {
          const sv = savings(p);
          return (
            <button
              key={p}
              onClick={() => onPeriodChange(p)}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
                period === p
                  ? 'bg-primary text-white'
                  : 'bg-bg text-text-secondary hover:text-text-primary'
              }`}
            >
              {PERIOD_NAMES[p]}
              {sv && <span className="ml-1 text-xs opacity-80">省{sv}%</span>}
            </button>
          );
        })}
      </div>

      <div className="space-y-3 mb-6">
        {(FEATURES[plan.id] ?? []).map((f, i) => (
          <div key={i} className="flex items-center gap-3">
            <div className="w-5 h-5 rounded-full bg-green-100 flex items-center justify-center flex-shrink-0">
              <Check className="w-3 h-3 text-green-600" />
            </div>
            <span className="text-text-primary text-sm">{f}</span>
          </div>
        ))}
      </div>

      {isCurrentPlan ? (
        <Button variant="secondary" size="lg" className="w-full" disabled>
          当前方案
        </Button>
      ) : isDowngrade ? (
        <Button variant="secondary" size="lg" className="w-full" disabled>
          无法降级
        </Button>
      ) : (
        <Button
          variant="primary"
          size="lg"
          className="w-full"
          onClick={() => onUpgrade(plan.id)}
          disabled={upgrading === plan.id}
        >
          {upgrading === plan.id ? (
            <><Loader2 className="animate-spin mr-2" size={18} />处理中...</>
          ) : (
            <>立即升级</>
          )}
        </Button>
      )}
    </Card>
  );
}

// ===== 主页面 =====

export default function PricingPage() {
  const router = useRouter();
  const { isAuthenticated, membershipTier } = useSharedAuth();
  const { showSuccess, showError } = useToast();
  const signInHref = '/auth/signin?callbackUrl=%2Fpricing';

  const [plans, setPlans] = useState<PricingPlan[]>(FALLBACK_PLANS);
  const [quotaPacks, setQuotaPacks] = useState<QuotaPack[]>(FALLBACK_PACKS);
  const [subscription, setSubscription] = useState<SubscriptionResponse | null>(null);
  const [quotaInfo, setQuotaInfo] = useState<QuotaInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [upgrading, setUpgrading] = useState<string | null>(null);
  const [purchasingPack, setPurchasingPack] = useState<string | null>(null);
  const [expandedFaq, setExpandedFaq] = useState<number | null>(null);
  const [period, setPeriod] = useState('monthly');

  useEffect(() => { loadData(); }, [isAuthenticated]);

  const loadData = async () => {
    try {
      setLoading(true);
      const [plansRes, packsRes] = await Promise.all([
        pricingApi.getPlans().catch(() => null),
        pricingApi.getQuotaPacks().catch(() => null),
      ]);
      if (plansRes?.plans?.length) setPlans(plansRes.plans);
      if (packsRes?.quota_packs?.length) setQuotaPacks(packsRes.quota_packs);

      if (isAuthenticated) {
        const [sub, quota] = await Promise.all([
          subscriptionApi.get().catch(() => null),
          quotaApi.get().catch(() => null),
        ]);
        if (sub) setSubscription(sub);
        if (quota) setQuotaInfo(quota);
      }
    } catch (err) {
      console.error('Failed to load data:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleUpgrade = async (planId: string) => {
    if (!isAuthenticated) { router.push(signInHref); return; }
    try {
      setUpgrading(planId);
      const result = await subscriptionApi.upgrade(planId, period);
      showSuccess(result.message || '订单已创建');
      await loadData();
    } catch (err: any) {
      showError(err.message || '升级失败，请重试');
    } finally {
      setUpgrading(null);
    }
  };

  const handlePurchasePack = async (packId: string) => {
    if (!isAuthenticated) { router.push(signInHref); return; }
    try {
      setPurchasingPack(packId);
      await quotaApi.purchasePack(packId);
      showSuccess('订单已创建');
      await loadData();
    } catch (err: any) {
      showError(err.message || '购买失败，请重试');
    } finally {
      setPurchasingPack(null);
    }
  };

  const currentTier = subscription?.feature_tier ?? membershipTier ?? 'free';
  const upgradablePlans = isAuthenticated ? getUpgradablePlans(currentTier, plans) : plans.filter((p) => p.id !== 'free');

  // ===== 渲染 =====

  if (loading) {
    return (
      <MainLayout>
        <div className="max-w-[1200px] mx-auto flex items-center justify-center py-20">
          <Loader2 className="animate-spin text-primary mr-4" size={40} />
          <p className="text-text-secondary text-lg">加载中...</p>
        </div>
      </MainLayout>
    );
  }

  return (
    <MainLayout>
      <div className="max-w-[1200px] mx-auto">
        {/* 页面标题 */}
        <div className="text-center mb-10">
          <div className="flex items-center justify-center gap-2 mb-3">
            <Crown className="text-primary" size={28} />
            <h1 className="font-heading text-[36px] font-semibold text-text-primary">我的套餐</h1>
          </div>
          <p className="text-text-secondary">管理您的订阅方案与配额</p>
        </div>

        {/* 当前套餐（已登录） */}
        {isAuthenticated && (
          <div className="mb-10">
            <CurrentPlanCard sub={subscription} quota={quotaInfo} />
          </div>
        )}

        {/* 方案对比 — 超级管理员无需展示 */}
        {currentTier !== 'superuser' && (
        <div className="mb-14">
          <h2 className="font-heading text-2xl font-semibold text-text-primary mb-6">
            {isAuthenticated ? '方案对比' : '选择方案'}
          </h2>
          <div className="grid md:grid-cols-3 gap-6">
            {plans.map((plan) => (
              <UpgradeCard
                key={plan.id}
                plan={plan}
                period={period}
                onPeriodChange={setPeriod}
                onUpgrade={handleUpgrade}
                upgrading={upgrading}
                isCurrentPlan={isAuthenticated && plan.id === currentTier}
                isDowngrade={isAuthenticated && (TIER_ORDER[plan.id] ?? 0) < (TIER_ORDER[currentTier] ?? 0)}
              />
            ))}
          </div>
        </div>
        )}

        {/* 未登录提示 */}
        {!isAuthenticated && (
          <div className="text-center mb-14">
            <p className="text-text-secondary mb-4">登录后查看当前套餐与升级选项</p>
            <Button variant="primary" size="lg" onClick={() => router.push(signInHref)}>
              登录 / 注册
              <ArrowRight className="ml-2" size={18} />
            </Button>
          </div>
        )}

        {/* 额度包 */}
        <div className="mb-14">
          <div className="flex items-center gap-2 mb-6">
            <Gift className="text-primary" size={24} />
            <h2 className="font-heading text-2xl font-semibold text-text-primary">额度包（按需购买）</h2>
          </div>
          <p className="text-text-secondary mb-6">配额用完了？购买额度包继续创作，购买后1年内有效</p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-2xl">
            {quotaPacks.map((pack) => (
              <Card key={pack.id} padding="lg">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="font-heading text-2xl font-semibold text-text-primary mb-1">{pack.quota} 次</div>
                    <div className="text-sm text-text-secondary">额度包</div>
                  </div>
                  <div className="text-right">
                    <div className="font-heading text-3xl font-bold text-primary mb-1">¥{formatPrice(pack.price)}</div>
                    <div className="text-sm text-text-tertiary">约 ¥{(pack.price / pack.quota / 100).toFixed(1)}/次</div>
                  </div>
                </div>
                <Button
                  variant="primary"
                  size="lg"
                  className="w-full mt-4"
                  onClick={() => handlePurchasePack(pack.id)}
                  disabled={purchasingPack === pack.id}
                >
                  {purchasingPack === pack.id ? (
                    <><Loader2 className="animate-spin mr-2" size={18} />购买中...</>
                  ) : '立即购买'}
                </Button>
              </Card>
            ))}
          </div>
        </div>

        {/* FAQ */}
        <Card padding="xl" className="mb-8">
          <div className="flex items-center gap-2 mb-8">
            <Shield className="text-primary" size={24} />
            <h2 className="font-heading text-2xl font-semibold text-text-primary">常见问题</h2>
          </div>
          <div className="space-y-4">
            {FAQS.map((faq, i) => (
              <div key={i} className="border border-border rounded-lg overflow-hidden">
                <button
                  onClick={() => setExpandedFaq(expandedFaq === i ? null : i)}
                  className="w-full flex items-center justify-between p-4 text-left hover:bg-bg transition-colors"
                >
                  <span className="font-body text-base font-medium text-text-primary">{faq.q}</span>
                  <svg
                    className={`w-5 h-5 text-text-secondary transition-transform ${expandedFaq === i ? 'rotate-180' : ''}`}
                    fill="none" stroke="currentColor" viewBox="0 0 24 24"
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </button>
                {expandedFaq === i && (
                  <div className="px-4 pb-4 pt-2 text-sm text-text-secondary border-t border-border">{faq.a}</div>
                )}
              </div>
            ))}
          </div>
        </Card>
      </div>
    </MainLayout>
  );
}
