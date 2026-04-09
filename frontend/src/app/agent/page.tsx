'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import {
  Bot,
  Plus,
  Trash2,
  Loader2,
  ToggleLeft,
  ToggleRight,
  FileText,
  CheckCircle,
  XCircle,
  Settings,
  Inbox,
  Flame,
  Clock,
  Edit2,
  Eye,
  Star,
  AlertCircle
} from 'lucide-react';
import MainLayout from '@/components/layout/MainLayout';
import Card from '@/components/ui/Card';
import Input from '@/components/ui/Input';
import Button from '@/components/ui/Button';
import Badge from '@/components/ui/Badge';
import { useToast } from '@/components/ui/ToastContainer';
import { agentApi, WritingAgent, AgentDraft, CreateAgentRequest, MembershipTier } from '@/types/api';
import { useAuth } from '@/hooks/useAuth';

// 平台选项
const PLATFORMS = [
  { value: 'wechat', label: '微信公众号', icon: '📱' },
  { value: 'zhihu', label: '知乎', icon: '💡' },
  { value: 'xiaohongshu', label: '小红书', icon: '📕' },
  { value: 'toutiao', label: '今日头条', icon: '📰' },
];

// 热点源选项
const HOTSPOT_SOURCES = [
  { value: 'baidu', label: '百度热搜', icon: '🔍' },
  { value: 'weibo', label: '微博热搜', icon: '📱' },
  { value: 'zhihu', label: '知乎热榜', icon: '💡' },
  { value: 'bilibili', label: 'B站热门', icon: '📺' },
  { value: 'toutiao', label: '头条热榜', icon: '📰' },
];

// 草稿状态映射
const DRAFT_STATUS_MAP: Record<string, { label: string; color: string }> = {
  pending: { label: '等待中', color: 'gray' },
  generating: { label: '生成中', color: 'blue' },
  completed: { label: '待审核', color: 'yellow' },
  reviewed: { label: '已接受', color: 'green' },
  discarded: { label: '已丢弃', color: 'red' },
};

// 会员限制配置
const AGENT_LIMITS: Record<MembershipTier, { maxAgents: number }> = {
  free: { maxAgents: 0 },
  pro: { maxAgents: 2 },
  ultra: { maxAgents: 10 },
  superuser: { maxAgents: 100 },
};

export default function AgentPage() {
  const router = useRouter();
  const { status, isAuthenticated, membershipTier, profileResolved } = useAuth();
  const { showSuccess, showError } = useToast();
  const signInHref = '/auth/signin?callbackUrl=%2Fagent';

  const authResolved = status !== 'loading';
  const tierResolved = !isAuthenticated || profileResolved;

  const [activeTab, setActiveTab] = useState<'agents' | 'drafts'>('agents');
  const [agents, setAgents] = useState<WritingAgent[]>([]);
  const [drafts, setDrafts] = useState<AgentDraft[]>([]);
  const [loading, setLoading] = useState(true);
  const [pageError, setPageError] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingAgent, setEditingAgent] = useState<WritingAgent | null>(null);

  // 创建表单状态
  const [formData, setFormData] = useState<CreateAgentRequest>({
    name: '',
    trigger_rules: {
      sources: [],
      keywords: [],
      min_heat: 100000,
    },
    platform: 'wechat',
    max_daily: 5,
  });
  const [keywordInput, setKeywordInput] = useState('');
  const [saving, setSaving] = useState(false);
  const [toggling, setToggling] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<string | null>(null);
  const [reviewing, setReviewing] = useState<string | null>(null);

  const limits = AGENT_LIMITS[membershipTier] || AGENT_LIMITS.free;
  const canCreateAgent = limits.maxAgents > 0 && agents.length < limits.maxAgents;
  const hasAgentAccess = membershipTier !== 'free';

  // 加载Agent列表
  const loadAgents = useCallback(async () => {
    if (!isAuthenticated || !tierResolved || !hasAgentAccess) return;
    try {
      const response = await agentApi.getAgents();
      setAgents(response.agents);
    } catch (error) {
      console.error('Failed to load agents:', error);
      const message = error instanceof Error ? error.message : '加载写作 Agent 失败，请重试';
      setPageError(message);
      showError(message);
    }
  }, [hasAgentAccess, isAuthenticated, showError, tierResolved]);

  // 加载草稿列表
  const loadDrafts = useCallback(async () => {
    if (!isAuthenticated || !tierResolved || !hasAgentAccess) return;
    try {
      const response = await agentApi.getDrafts();
      setDrafts(response.drafts);
    } catch (error) {
      console.error('Failed to load drafts:', error);
      const message = error instanceof Error ? error.message : '加载草稿失败，请重试';
      setPageError(message);
      showError(message);
    }
  }, [hasAgentAccess, isAuthenticated, showError, tierResolved]);

  useEffect(() => {
    if (status === 'authenticated' && tierResolved) {
      if (!hasAgentAccess) {
        setAgents([]);
        setDrafts([]);
        setPageError(null);
        setLoading(false);
        return;
      }
      setPageError(null);
      setLoading(true);
      Promise.all([loadAgents(), loadDrafts()]).finally(() => setLoading(false));
    } else if (status === 'unauthenticated') {
      setAgents([]);
      setDrafts([]);
      setPageError(null);
      setLoading(false);
    } else {
      setLoading(true);
    }
  }, [status, loadAgents, loadDrafts, tierResolved, hasAgentAccess]);

  // 处理关键词输入
  const handleAddKeyword = () => {
    if (!keywordInput.trim()) return;
    setFormData(prev => ({
      ...prev,
      trigger_rules: {
        ...prev.trigger_rules,
        keywords: [...(prev.trigger_rules.keywords || []), keywordInput.trim()],
      },
    }));
    setKeywordInput('');
  };

  const handleRemoveKeyword = (index: number) => {
    setFormData(prev => ({
      ...prev,
      trigger_rules: {
        ...prev.trigger_rules,
        keywords: prev.trigger_rules.keywords?.filter((_, i) => i !== index) || [],
      },
    }));
  };

  // 切换热点源
  const toggleSource = (source: string) => {
    setFormData(prev => {
      const sources = prev.trigger_rules.sources || [];
      const newSources = sources.includes(source)
        ? sources.filter(s => s !== source)
        : [...sources, source];
      return {
        ...prev,
        trigger_rules: { ...prev.trigger_rules, sources: newSources },
      };
    });
  };

  // 创建或更新Agent
  const handleSaveAgent = async () => {
    if (!formData.name.trim()) {
      showError('请输入Agent名称');
      return;
    }
    if (formData.trigger_rules.sources.length === 0) {
      showError('请选择至少一个热点源');
      return;
    }

    setSaving(true);
    try {
      if (editingAgent) {
        await agentApi.updateAgent(editingAgent.id, formData);
        showSuccess('Agent更新成功');
      } else {
        await agentApi.createAgent(formData);
        showSuccess('Agent创建成功');
      }
      setShowCreateModal(false);
      setEditingAgent(null);
      resetForm();
      await loadAgents();
    } catch (error) {
      console.error('Failed to save agent:', error);
      showError(error instanceof Error ? error.message : editingAgent ? '更新Agent失败' : '创建Agent失败');
    } finally {
      setSaving(false);
    }
  };

  // 切换Agent状态
  const handleToggleAgent = async (agent: WritingAgent) => {
    setToggling(agent.id);
    try {
      await agentApi.updateAgent(agent.id, { is_active: !agent.is_active });
      setAgents(prev =>
        prev.map(a => (a.id === agent.id ? { ...a, is_active: !agent.is_active } : a))
      );
      showSuccess(agent.is_active ? 'Agent已禁用' : 'Agent已启用');
    } catch (error) {
      console.error('Failed to toggle agent:', error);
      showError(error instanceof Error ? error.message : '操作失败');
    } finally {
      setToggling(null);
    }
  };

  // 删除Agent
  const handleDeleteAgent = async (agentId: string) => {
    if (!confirm('确定要删除这个Agent吗？')) return;

    setDeleting(agentId);
    try {
      await agentApi.deleteAgent(agentId);
      showSuccess('Agent已删除');
      await loadAgents();
    } catch (error) {
      console.error('Failed to delete agent:', error);
      showError(error instanceof Error ? error.message : '删除失败');
    } finally {
      setDeleting(null);
    }
  };

  // 编辑Agent
  const handleEditAgent = (agent: WritingAgent) => {
    setEditingAgent(agent);
    setFormData({
      name: agent.name,
      trigger_rules: agent.trigger_rules,
      platform: agent.platform,
      max_daily: agent.max_daily,
    });
    setShowCreateModal(true);
  };

  // 重置表单
  const resetForm = () => {
    setFormData({
      name: '',
      trigger_rules: {
        sources: [],
        keywords: [],
        min_heat: 100000,
      },
      platform: 'wechat',
      max_daily: 5,
    });
    setKeywordInput('');
  };

  // 审核草稿
  const handleReviewDraft = async (draftId: string, action: 'accept' | 'discard') => {
    setReviewing(draftId);
    try {
      await agentApi.reviewDraft(draftId, action);
      showSuccess(action === 'accept' ? '已接受草稿' : '已丢弃草稿');
      await loadDrafts();
    } catch (error) {
      console.error('Failed to review draft:', error);
      showError(error instanceof Error ? error.message : '操作失败');
    } finally {
      setReviewing(null);
    }
  };

  // 格式化日期
  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('zh-CN', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  // 格式化热度
  const formatHeat = (heat?: number) => {
    if (!heat) return '-';
    if (heat >= 10000) {
      return `${(heat / 10000).toFixed(1)}万`;
    }
    return heat.toString();
  };

  const handleRetryLoad = async () => {
    setPageError(null);
    setLoading(true);
    await Promise.all([loadAgents(), loadDrafts()]);
    setLoading(false);
  };

  useEffect(() => {
    if (status !== 'unauthenticated') {
      return;
    }
    router.replace(signInHref);
  }, [router, signInHref, status]);

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

  // Free会员限制
  if (tierResolved && !hasAgentAccess) {
    return (
      <MainLayout>
        <div className="max-w-[1376px] mx-auto">
          <div className="flex items-center gap-3 mb-8">
            <span className="text-[32px]">🤖</span>
            <div>
              <h1 className="font-heading text-[32px] font-semibold text-text-primary">
                写作 Agent
              </h1>
              <p className="font-body text-base text-text-secondary mt-1">
                智能代理系统自动监控热点，自动生成文章草稿
              </p>
            </div>
          </div>

          <Card padding="lg" className="text-center py-16">
            <Bot size={64} className="text-text-tertiary mx-auto mb-4" />
            <h3 className="text-lg font-medium text-text-primary mb-2">Pro会员专属功能</h3>
            <p className="text-text-secondary mb-6 max-w-md mx-auto">
              写作 Agent 是 Pro 及以上会员的专属功能。升级会员即可创建 Agent，让 AI 自动监控热点并生成文章草稿。
            </p>
            <Button variant="primary" onClick={() => router.push('/pricing')}>
              升级会员
            </Button>
          </Card>
        </div>
      </MainLayout>
    );
  }

  return (
    <MainLayout>
      <div className="max-w-[1376px] mx-auto">
        {/* 页面标题 */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-3">
            <span className="text-[32px]">🤖</span>
            <div>
              <h1 className="font-heading text-[32px] font-semibold text-text-primary">
                写作 Agent
              </h1>
              <p className="font-body text-base text-text-secondary mt-1">
                智能代理系统自动监控热点，自动生成文章草稿
              </p>
            </div>
          </div>
        </div>

        {/* Tab切换 */}
        <div className="flex gap-4 mb-6 border-b border-border">
          <button
            onClick={() => setActiveTab('agents')}
            className={`flex items-center gap-2 px-4 py-3 font-medium transition-colors border-b-2 ${
              activeTab === 'agents'
                ? 'text-primary border-primary'
                : 'text-text-secondary border-transparent hover:text-text-primary'
            }`}
          >
            <Settings size={18} />
            Agent管理
            <Badge variant="default" className="ml-1">{agents.length}</Badge>
          </button>
          <button
            onClick={() => setActiveTab('drafts')}
            className={`flex items-center gap-2 px-4 py-3 font-medium transition-colors border-b-2 ${
              activeTab === 'drafts'
                ? 'text-primary border-primary'
                : 'text-text-secondary border-transparent hover:text-text-primary'
            }`}
          >
            <Inbox size={18} />
            草稿箱
            <Badge variant="default" className="ml-1">
              {drafts.filter(d => d.status === 'completed').length}
            </Badge>
          </button>
        </div>

        {pageError && agents.length === 0 && drafts.length === 0 && (
          <Card padding="lg" className="text-center py-16 mb-6">
            <AlertCircle size={64} className="text-red-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-text-primary mb-2">加载写作 Agent 失败</h3>
            <p className="text-text-secondary mb-6">{pageError}</p>
            <Button variant="primary" onClick={handleRetryLoad}>
              重新加载
            </Button>
          </Card>
        )}

        {/* Agent管理 Tab */}
        {activeTab === 'agents' && (
          <>
            <div className="flex justify-between items-center mb-6">
              <div className="text-sm text-text-secondary">
                已创建 {agents.length} / {limits.maxAgents} 个Agent
              </div>
              <Button
                variant="primary"
                onClick={() => {
                  setEditingAgent(null);
                  resetForm();
                  setShowCreateModal(true);
                }}
                disabled={!canCreateAgent}
                className="flex items-center gap-2"
              >
                <Plus size={18} />
                新建Agent
              </Button>
            </div>

            {agents.length === 0 ? (
              <Card padding="lg" className="text-center py-16">
                <Bot size={64} className="text-text-tertiary mx-auto mb-4" />
                <h3 className="text-lg font-medium text-text-primary mb-2">还没有写作 Agent</h3>
                <p className="text-text-secondary mb-6">创建您的第一个Agent，让AI自动监控热点并生成文章</p>
                <Button variant="primary" onClick={() => setShowCreateModal(true)}>
                  <Plus size={18} className="mr-2" />
                  新建Agent
                </Button>
              </Card>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {agents.map((agent) => (
                  <Card key={agent.id} padding="lg" className="hover:shadow-lg transition-shadow">
                    <div className="flex items-start justify-between mb-4">
                      <div className="flex items-center gap-3">
                        <div className="w-12 h-12 bg-primary/10 rounded-xl flex items-center justify-center">
                          <Bot size={24} className="text-primary" />
                        </div>
                        <div>
                          <h3 className="font-medium text-text-primary">{agent.name}</h3>
                          <p className="text-sm text-text-tertiary">
                            {PLATFORMS.find(p => p.value === agent.platform)?.label || agent.platform}
                          </p>
                        </div>
                      </div>
                      <button
                        onClick={() => handleToggleAgent(agent)}
                        disabled={!!toggling}
                        className={`transition-colors ${
                          agent.is_active
                            ? 'text-primary hover:text-primary/80'
                            : 'text-text-tertiary hover:text-text-secondary'
                        }`}
                      >
                        {toggling === agent.id ? (
                          <Loader2 size={28} className="animate-spin" />
                        ) : agent.is_active ? (
                          <ToggleRight size={28} />
                        ) : (
                          <ToggleLeft size={28} />
                        )}
                      </button>
                    </div>

                    {/* 统计信息 */}
                    <div className="grid grid-cols-3 gap-4 mb-4">
                      <div className="text-center p-3 bg-bg rounded-lg">
                        <div className="text-lg font-semibold text-text-primary">
                          {agent.today_triggered}
                        </div>
                        <div className="text-xs text-text-tertiary">今日生成</div>
                      </div>
                      <div className="text-center p-3 bg-bg rounded-lg">
                        <div className="text-lg font-semibold text-text-primary">
                          {agent.max_daily}
                        </div>
                        <div className="text-xs text-text-tertiary">每日上限</div>
                      </div>
                      <div className="text-center p-3 bg-bg rounded-lg">
                        <div className="text-lg font-semibold text-text-primary">
                          {agent.total_triggered}
                        </div>
                        <div className="text-xs text-text-tertiary">总计生成</div>
                      </div>
                    </div>

                    {/* 触发规则 */}
                    <div className="space-y-2 mb-4">
                      <div className="flex items-center gap-2 text-sm">
                        <span className="text-text-tertiary">监控源:</span>
                        <div className="flex gap-1">
                          {agent.trigger_rules.sources.map(source => (
                            <span key={source} className="text-text-primary">
                              {HOTSPOT_SOURCES.find(s => s.value === source)?.icon || source}
                            </span>
                          ))}
                        </div>
                      </div>
                      {agent.trigger_rules.keywords && agent.trigger_rules.keywords.length > 0 && (
                        <div className="flex items-center gap-2 text-sm">
                          <span className="text-text-tertiary">关键词:</span>
                          <div className="flex flex-wrap gap-1">
                            {agent.trigger_rules.keywords.map((keyword, idx) => (
                              <Badge key={idx} variant="default" className="text-xs">
                                {keyword}
                              </Badge>
                            ))}
                          </div>
                        </div>
                      )}
                      {agent.trigger_rules.min_heat && (
                        <div className="flex items-center gap-2 text-sm">
                          <span className="text-text-tertiary">最小热度:</span>
                          <span className="text-text-primary">{formatHeat(agent.trigger_rules.min_heat)}</span>
                        </div>
                      )}
                    </div>

                    {/* 操作按钮 */}
                    <div className="flex gap-2">
                      <Button
                        variant="secondary"
                        size="sm"
                        className="flex-1"
                        onClick={() => handleEditAgent(agent)}
                      >
                        <Edit2 size={16} className="mr-1" />
                        编辑
                      </Button>
                      <button
                        onClick={() => handleDeleteAgent(agent.id)}
                        disabled={!!deleting}
                        className="p-2 text-text-tertiary hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors disabled:opacity-50"
                      >
                        {deleting === agent.id ? (
                          <Loader2 size={16} className="animate-spin" />
                        ) : (
                          <Trash2 size={16} />
                        )}
                      </button>
                    </div>
                  </Card>
                ))}
              </div>
            )}
          </>
        )}

        {/* 草稿箱 Tab */}
        {activeTab === 'drafts' && (
          <>
            {drafts.length === 0 ? (
              <Card padding="lg" className="text-center py-16">
                <Inbox size={64} className="text-text-tertiary mx-auto mb-4" />
                <h3 className="text-lg font-medium text-text-primary mb-2">草稿箱为空</h3>
                <p className="text-text-secondary">当Agent生成文章草稿后，会显示在这里等待您的审核</p>
              </Card>
            ) : (
              <div className="space-y-4">
                {drafts.map((draft) => {
                  const statusConfig = DRAFT_STATUS_MAP[draft.status] || DRAFT_STATUS_MAP.pending;
                  return (
                    <Card key={draft.id} padding="lg" className="hover:shadow-md transition-shadow">
                      <div className="flex items-start justify-between">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-2">
                            <Badge variant={statusConfig.color as any}>{statusConfig.label}</Badge>
                            <span className="text-sm text-text-tertiary">{draft.agent_name}</span>
                          </div>
                          <h3 className="font-medium text-text-primary mb-2">{draft.hotspot_title}</h3>
                          <div className="flex items-center gap-4 text-sm text-text-tertiary">
                            <span className="flex items-center gap-1">
                              <Flame size={14} />
                              {formatHeat(draft.hotspot_heat)}
                            </span>
                            <span className="flex items-center gap-1">
                              <Clock size={14} />
                              {formatDate(draft.created_at)}
                            </span>
                          </div>
                        </div>

                        {draft.status === 'completed' && (
                          <div className="flex gap-2 ml-4">
                            <Button
                              variant="primary"
                              size="sm"
                              onClick={() => handleReviewDraft(draft.id, 'accept')}
                              disabled={!!reviewing}
                            >
                              {reviewing === draft.id ? (
                                <Loader2 size={16} className="animate-spin" />
                              ) : (
                                <CheckCircle size={16} className="mr-1" />
                              )}
                              接受
                            </Button>
                            <Button
                              variant="secondary"
                              size="sm"
                              onClick={() => handleReviewDraft(draft.id, 'discard')}
                              disabled={!!reviewing}
                            >
                              <XCircle size={16} className="mr-1" />
                              丢弃
                            </Button>
                          </div>
                        )}

                        {draft.article_id && (
                          <Button
                            variant="secondary"
                            size="sm"
                            onClick={() => router.push(`/history/${draft.article_id}`)}
                            className="ml-4"
                          >
                            <Eye size={16} className="mr-1" />
                            查看
                          </Button>
                        )}
                      </div>
                    </Card>
                  );
                })}
              </div>
            )}
          </>
        )}

        {/* 创建/编辑 Agent Modal */}
        {showCreateModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center">
            <div
              className="absolute inset-0 bg-black/50 backdrop-blur-sm"
              onClick={() => setShowCreateModal(false)}
            />
            <div className="relative bg-white rounded-xl shadow-xl w-full max-w-2xl max-h-[90vh] overflow-hidden animate-in fade-in zoom-in-95 duration-200">
              <div className="flex items-center justify-between p-6 border-b border-border">
                <h2 className="text-xl font-semibold text-text-primary">
                  {editingAgent ? '编辑 Agent' : '新建写作 Agent'}
                </h2>
                <button
                  onClick={() => setShowCreateModal(false)}
                  className="text-text-secondary hover:text-text-primary transition-colors"
                >
                  <XCircle size={24} />
                </button>
              </div>

              <div className="p-6 overflow-y-auto max-h-[calc(90vh-180px)]">
                <div className="space-y-6">
                  {/* Agent名称 */}
                  <div>
                    <label className="block text-sm font-medium text-text-primary mb-2">
                      Agent名称 <span className="text-red-500">*</span>
                    </label>
                    <Input
                      value={formData.name}
                      onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                      placeholder="例如：科技热点追踪"
                    />
                  </div>

                  {/* 监控热点源 */}
                  <div>
                    <label className="block text-sm font-medium text-text-primary mb-2">
                      监控热点源 <span className="text-red-500">*</span>
                    </label>
                    <div className="grid grid-cols-3 sm:grid-cols-5 gap-3">
                      {HOTSPOT_SOURCES.map((source) => (
                        <button
                          key={source.value}
                          onClick={() => toggleSource(source.value)}
                          className={`p-3 rounded-xl border-2 transition-all ${
                            formData.trigger_rules.sources?.includes(source.value)
                              ? 'border-primary bg-primary/5'
                              : 'border-border hover:border-primary/50'
                          }`}
                        >
                          <span className="text-2xl mb-1 block">{source.icon}</span>
                          <span className="text-xs text-text-primary">{source.label}</span>
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* 关键词匹配 */}
                  <div>
                    <label className="block text-sm font-medium text-text-primary mb-2">
                      关键词匹配 <span className="text-text-tertiary font-normal">(可选)</span>
                    </label>
                    <div className="flex gap-2 mb-2">
                      <Input
                        value={keywordInput}
                        onChange={(e) => setKeywordInput(e.target.value)}
                        placeholder="输入关键词后按回车添加"
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') {
                            e.preventDefault();
                            handleAddKeyword();
                          }
                        }}
                      />
                      <Button variant="secondary" onClick={handleAddKeyword}>
                        添加
                      </Button>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {formData.trigger_rules.keywords?.map((keyword, index) => (
                        <Badge key={index} variant="default" className="flex items-center gap-1">
                          {keyword}
                          <button
                            onClick={() => handleRemoveKeyword(index)}
                            className="hover:text-red-500"
                          >
                            <XCircle size={14} />
                          </button>
                        </Badge>
                      ))}
                    </div>
                  </div>

                  {/* 热度阈值 */}
                  <div>
                    <label className="block text-sm font-medium text-text-primary mb-2">
                      最小热度阈值: {formatHeat(formData.trigger_rules.min_heat)}
                    </label>
                    <input
                      type="range"
                      min={10000}
                      max={500000}
                      step={10000}
                      value={formData.trigger_rules.min_heat}
                      onChange={(e) =>
                        setFormData(prev => ({
                          ...prev,
                          trigger_rules: {
                            ...prev.trigger_rules,
                            min_heat: parseInt(e.target.value),
                          },
                        }))
                      }
                      className="w-full"
                    />
                    <div className="flex justify-between text-xs text-text-tertiary mt-1">
                      <span>1万</span>
                      <span>25万</span>
                      <span>50万</span>
                    </div>
                  </div>

                  {/* 输出平台 */}
                  <div>
                    <label className="block text-sm font-medium text-text-primary mb-2">
                      默认输出平台
                    </label>
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                      {PLATFORMS.map((platform) => (
                        <button
                          key={platform.value}
                          onClick={() => setFormData(prev => ({ ...prev, platform: platform.value }))}
                          className={`p-3 rounded-xl border-2 transition-all ${
                            formData.platform === platform.value
                              ? 'border-primary bg-primary/5'
                              : 'border-border hover:border-primary/50'
                          }`}
                        >
                          <span className="text-2xl mb-1 block">{platform.icon}</span>
                          <span className="text-sm text-text-primary">{platform.label}</span>
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* 每日上限 */}
                  <div>
                    <label className="block text-sm font-medium text-text-primary mb-2">
                      每日生成上限: {formData.max_daily} 篇
                    </label>
                    <input
                      type="range"
                      min={1}
                      max={20}
                      value={formData.max_daily}
                      onChange={(e) =>
                        setFormData(prev => ({ ...prev, max_daily: parseInt(e.target.value) }))
                      }
                      className="w-full"
                    />
                    <div className="flex justify-between text-xs text-text-tertiary mt-1">
                      <span>1</span>
                      <span>10</span>
                      <span>20</span>
                    </div>
                  </div>
                </div>
              </div>

              <div className="flex gap-3 p-6 border-t border-border">
                <Button
                  variant="secondary"
                  onClick={() => setShowCreateModal(false)}
                  className="flex-1"
                >
                  取消
                </Button>
                <Button
                  variant="primary"
                  onClick={handleSaveAgent}
                  disabled={
                    saving ||
                    !formData.name.trim() ||
                    formData.trigger_rules.sources.length === 0
                  }
                  className="flex-1"
                >
                  {saving ? (
                    <>
                      <Loader2 size={18} className="animate-spin mr-2" />
                      保存中...
                    </>
                  ) : (
                    <>
                      <Plus size={18} className="mr-2" />
                      {editingAgent ? '保存修改' : '创建Agent'}
                    </>
                  )}
                </Button>
              </div>
            </div>
          </div>
        )}
      </div>
    </MainLayout>
  );
}
