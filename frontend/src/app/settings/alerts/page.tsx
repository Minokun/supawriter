'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { Bell, Plus, Trash2, Loader2, Sparkles, Lightbulb, Tag, ToggleLeft, ToggleRight, AlertCircle } from 'lucide-react';
import MainLayout from '@/components/layout/MainLayout';
import Card from '@/components/ui/Card';
import Input from '@/components/ui/Input';
import Button from '@/components/ui/Button';
import Badge from '@/components/ui/Badge';
import { useToast } from '@/components/ui/ToastContainer';
import { alertsApi, AlertKeyword, MembershipTier } from '@/types/api';
import { useAuth } from '@/hooks/useAuth';
import { SettingsStateCard } from '@/components/settings/SettingsStateCard';
import { getBackendToken } from '@/lib/api';

// 关键词限制配置
const KEYWORD_LIMITS: Record<MembershipTier, number> = {
  free: 1,
  pro: 5,
  ultra: Infinity,
  superuser: Infinity,
};

// 分类选项
const CATEGORIES = [
  { value: '', label: '无分类' },
  { value: 'tech', label: '科技' },
  { value: 'finance', label: '财经' },
  { value: 'entertainment', label: '娱乐' },
  { value: 'sports', label: '体育' },
  { value: 'politics', label: '时政' },
  { value: 'social', label: '社会' },
  { value: 'other', label: '其他' },
];

export default function AlertSettingsPage() {
  const router = useRouter();
  const { status, isAuthenticated, membershipTier } = useAuth();
  const { showSuccess, showError } = useToast();
  const signInHref = '/auth/signin?callbackUrl=%2Fsettings%2Falerts';

  const [keywords, setKeywords] = useState<AlertKeyword[]>([]);
  const [suggestedKeywords, setSuggestedKeywords] = useState<string[]>([]);
  const [newKeyword, setNewKeyword] = useState('');
  const [newCategory, setNewCategory] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [loadingSuggestions, setLoadingSuggestions] = useState(false);

  const keywordLimit = KEYWORD_LIMITS[membershipTier] || 1;
  const canAddMore = keywordLimit === Infinity || keywords.length < keywordLimit;

  const ensureBackendTokenReady = useCallback(async () => {
    if (!isAuthenticated) return null;

    const existingToken = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
    if (existingToken) {
      return existingToken;
    }

    return getBackendToken();
  }, [isAuthenticated]);

  // 加载关键词列表
  const loadKeywords = useCallback(async () => {
    if (!isAuthenticated) return;
    setLoading(true);
    try {
      if (!(await ensureBackendTokenReady())) {
        throw new Error('Missing backend token');
      }

      const response = await alertsApi.getKeywords();
      setKeywords(response.keywords);
    } catch (error) {
      console.error('Failed to load keywords:', error);
      showError('加载关键词失败');
    } finally {
      setLoading(false);
    }
  }, [ensureBackendTokenReady, isAuthenticated, showError]);

  // 加载AI推荐关键词
  const loadSuggestions = useCallback(async () => {
    if (!isAuthenticated) return;
    setLoadingSuggestions(true);
    try {
      if (!(await ensureBackendTokenReady())) {
        throw new Error('Missing backend token');
      }

      const response = await alertsApi.suggestKeywords();
      setSuggestedKeywords(response.keywords.slice(0, 5)); // 最多显示5个
    } catch (error) {
      console.error('Failed to load suggestions:', error);
      // 静默失败，不显示错误
    } finally {
      setLoadingSuggestions(false);
    }
  }, [ensureBackendTokenReady, isAuthenticated]);

  useEffect(() => {
    if (status === 'authenticated') {
      loadKeywords();
      loadSuggestions();
    } else if (status === 'unauthenticated') {
      setLoading(false);
    }
  }, [status, loadKeywords, loadSuggestions]);

  // 添加关键词
  const handleAddKeyword = async () => {
    if (!newKeyword.trim()) {
      showError('请输入关键词');
      return;
    }

    if (!canAddMore) {
      showError(`您的会员等级最多可设置 ${keywordLimit} 个关键词`);
      return;
    }

    setSaving(true);
    try {
      if (!(await ensureBackendTokenReady())) {
        throw new Error('Missing backend token');
      }

      await alertsApi.addKeyword(newKeyword.trim(), newCategory || undefined);
      showSuccess('关键词添加成功');
      setNewKeyword('');
      setNewCategory('');
      await loadKeywords();
    } catch (error) {
      showError('添加关键词失败');
    } finally {
      setSaving(false);
    }
  };

  // 删除关键词
  const handleDeleteKeyword = async (id: string) => {
    if (!confirm('确定要删除这个关键词吗？')) return;

    try {
      if (!(await ensureBackendTokenReady())) {
        throw new Error('Missing backend token');
      }

      await alertsApi.deleteKeyword(id);
      showSuccess('关键词已删除');
      await loadKeywords();
    } catch (error) {
      showError('删除失败');
    }
  };

  // 切换关键词状态
  const handleToggleKeyword = async (id: string, currentStatus: boolean) => {
    try {
      if (!(await ensureBackendTokenReady())) {
        throw new Error('Missing backend token');
      }

      await alertsApi.toggleKeyword(id, !currentStatus);
      setKeywords(prev =>
        prev.map(k => (k.id === id ? { ...k, is_active: !currentStatus } : k))
      );
      showSuccess(currentStatus ? '关键词已禁用' : '关键词已启用');
    } catch (error) {
      showError('操作失败');
    }
  };

  // 添加推荐关键词
  const handleAddSuggested = async (keyword: string) => {
    if (!canAddMore) {
      showError(`您的会员等级最多可设置 ${keywordLimit} 个关键词`);
      return;
    }

    setSaving(true);
    try {
      if (!(await ensureBackendTokenReady())) {
        throw new Error('Missing backend token');
      }

      await alertsApi.addKeyword(keyword);
      showSuccess('关键词添加成功');
      await loadKeywords();
      // 从推荐列表中移除已添加的
      setSuggestedKeywords(prev => prev.filter(k => k !== keyword));
    } catch (error) {
      showError('添加关键词失败');
    } finally {
      setSaving(false);
    }
  };

  // 获取分类标签
  const getCategoryLabel = (category?: string) => {
    const cat = CATEGORIES.find(c => c.value === category);
    return cat?.label || '无分类';
  };

  // 格式化日期
  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('zh-CN', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  if (status === 'loading' || loading) {
    return (
      <MainLayout>
        <div className="max-w-[1376px] mx-auto">
          <SettingsStateCard mode="loading" statusText="加载中..." />
        </div>
      </MainLayout>
    );
  }

  if (status === 'unauthenticated') {
    return (
      <MainLayout>
        <div className="max-w-[1376px] mx-auto">
          <SettingsStateCard
            mode="auth"
            authMessage="请先登录以访问热点预警设置"
            signinHref={signInHref}
          />
        </div>
      </MainLayout>
    );
  }

  return (
    <MainLayout>
      <div className="max-w-[1376px] mx-auto">
        <button
          onClick={() => router.push('/settings')}
          className="mb-4 inline-flex items-center text-sm text-text-secondary hover:text-primary transition-colors"
        >
          ← 返回系统设置
        </button>
        {/* 页面标题 */}
        <div className="flex items-center gap-3 mb-8">
          <span className="text-[32px]">🔔</span>
          <div>
            <h1 className="font-heading text-[32px] font-semibold text-text-primary">
              热点预警设置
            </h1>
            <p className="font-body text-base text-text-secondary mt-1">
              设置关注的关键词，当热点匹配时我们会通知您
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* 左侧：关键词管理 */}
          <div className="lg:col-span-2 space-y-6">
            {/* 添加关键词卡片 */}
            <Card padding="lg">
              <div className="flex items-center gap-2 mb-4">
                <Plus className="text-primary" size={24} />
                <h2 className="font-heading text-xl font-semibold text-text-primary">
                  添加关键词
                </h2>
              </div>

              <div className="flex flex-col sm:flex-row gap-3">
                <div className="flex-1">
                  <Input
                    value={newKeyword}
                    onChange={(e) => setNewKeyword(e.target.value)}
                    placeholder="输入关键词（如：人工智能、比特币）"
                    disabled={!canAddMore || saving}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') handleAddKeyword();
                    }}
                  />
                </div>
                <select
                  value={newCategory}
                  onChange={(e) => setNewCategory(e.target.value)}
                  disabled={!canAddMore || saving}
                  className="h-12 px-4 bg-surface border-[1.5px] border-border rounded-lg font-body text-[15px] text-text-primary focus:border-primary focus:outline-none focus:ring-3 focus:ring-primary/10 transition-all"
                >
                  {CATEGORIES.map(cat => (
                    <option key={cat.value} value={cat.value}>
                      {cat.label}
                    </option>
                  ))}
                </select>
                <Button
                  variant="primary"
                  onClick={handleAddKeyword}
                  disabled={!canAddMore || saving || !newKeyword.trim()}
                  className="whitespace-nowrap"
                >
                  {saving ? (
                    <Loader2 className="animate-spin" size={18} />
                  ) : (
                    <Plus size={18} />
                  )}
                  添加
                </Button>
              </div>

              {!canAddMore && (
                <div className="mt-3 p-3 bg-amber-50 border border-amber-200 rounded-lg flex items-center gap-2 text-amber-700 text-sm">
                  <AlertCircle size={16} />
                  <span>
                    您的会员等级最多可设置 {keywordLimit} 个关键词。
                    <button
                      onClick={() => router.push('/pricing')}
                      className="underline font-medium ml-1 hover:text-amber-800"
                    >
                      升级会员
                    </button>
                    以添加更多
                  </span>
                </div>
              )}

              <div className="mt-3 text-sm text-text-tertiary">
                已设置 {keywords.length} / {keywordLimit === Infinity ? '无限制' : keywordLimit} 个关键词
              </div>
            </Card>

            {/* 关键词列表 */}
            <Card padding="lg">
              <div className="flex items-center gap-2 mb-4">
                <Bell className="text-primary" size={24} />
                <h2 className="font-heading text-xl font-semibold text-text-primary">
                  我的关键词
                </h2>
              </div>

              {keywords.length === 0 ? (
                <div className="text-center py-12">
                  <Bell size={48} className="text-text-tertiary mx-auto mb-4" />
                  <p className="text-text-secondary mb-2">还没有设置关键词</p>
                  <p className="text-sm text-text-tertiary">
                    添加一个关键词开始接收热点预警
                  </p>
                </div>
              ) : (
                <div className="space-y-3">
                  {keywords.map((keyword) => (
                    <div
                      key={keyword.id}
                      className={`flex items-center justify-between p-4 rounded-xl border transition-all ${
                        keyword.is_active
                          ? 'bg-white border-border'
                          : 'bg-bg border-border/50'
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        <button
                          onClick={() => handleToggleKeyword(keyword.id, keyword.is_active)}
                          className={`transition-colors ${
                            keyword.is_active
                              ? 'text-primary hover:text-primary/80'
                              : 'text-text-tertiary hover:text-text-secondary'
                          }`}
                          title={keyword.is_active ? '点击禁用' : '点击启用'}
                        >
                          {keyword.is_active ? (
                            <ToggleRight size={28} />
                          ) : (
                            <ToggleLeft size={28} />
                          )}
                        </button>

                        <div>
                          <div className="flex items-center gap-2">
                            <span
                              className={`font-medium ${
                                keyword.is_active ? 'text-text-primary' : 'text-text-tertiary'
                              }`}
                            >
                              {keyword.keyword}
                            </span>
                            {keyword.category && (
                              <Badge variant="default" className="text-xs">
                                {getCategoryLabel(keyword.category)}
                              </Badge>
                            )}
                          </div>
                          <span className="text-xs text-text-tertiary">
                            创建于 {formatDate(keyword.created_at)}
                          </span>
                        </div>
                      </div>

                      <button
                        onClick={() => handleDeleteKeyword(keyword.id)}
                        className="p-2 text-text-tertiary hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
                        title="删除"
                      >
                        <Trash2 size={18} />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </Card>
          </div>

          {/* 右侧：AI推荐 */}
          <div className="lg:col-span-1">
            <Card padding="lg">
              <div className="flex items-center gap-2 mb-4">
                <Sparkles className="text-amber-500" size={24} />
                <h2 className="font-heading text-xl font-semibold text-text-primary">
                  AI推荐关键词
                </h2>
              </div>

              <p className="text-sm text-text-secondary mb-4">
                根据您的文章历史，AI为您推荐以下关键词
              </p>

              {loadingSuggestions ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="animate-spin text-primary" size={24} />
                </div>
              ) : suggestedKeywords.length === 0 ? (
                <div className="text-center py-8">
                  <Lightbulb size={32} className="text-text-tertiary mx-auto mb-2" />
                  <p className="text-sm text-text-secondary">
                    暂无推荐，多写几篇文章后AI会为您推荐
                  </p>
                </div>
              ) : (
                <div className="space-y-2">
                  {suggestedKeywords.map((keyword, index) => (
                    <div
                      key={index}
                      className="flex items-center justify-between p-3 bg-bg rounded-lg group hover:bg-primary/5 transition-colors"
                    >
                      <span className="text-text-primary font-medium">{keyword}</span>
                      <button
                        onClick={() => handleAddSuggested(keyword)}
                        disabled={!canAddMore || saving}
                        className="opacity-0 group-hover:opacity-100 p-1.5 text-primary hover:bg-primary/10 rounded transition-all disabled:opacity-50"
                        title="添加"
                      >
                        <Plus size={16} />
                      </button>
                    </div>
                  ))}
                </div>
              )}

              <div className="mt-4 pt-4 border-t border-border">
                <button
                  onClick={loadSuggestions}
                  disabled={loadingSuggestions}
                  className="text-sm text-primary hover:text-primary/80 flex items-center gap-1"
                >
                  {loadingSuggestions && (
                    <Loader2 className="animate-spin" size={14} />
                  )}
                  刷新推荐
                </button>
              </div>
            </Card>

            {/* 使用提示 */}
            <Card padding="md" className="mt-4">
              <div className="flex items-start gap-3">
                <Lightbulb className="text-amber-500 flex-shrink-0 mt-0.5" size={18} />
                <div className="text-sm text-text-secondary">
                  <p className="font-medium text-text-primary mb-1">使用提示</p>
                  <ul className="space-y-1 text-text-tertiary">
                    <li>• 关键词越具体，匹配越精准</li>
                    <li>• 系统每30分钟扫描一次热点</li>
                    <li>• 匹配成功后会通过通知中心提醒</li>
                  </ul>
                </div>
              </div>
            </Card>
          </div>
        </div>
      </div>
    </MainLayout>
  );
}
