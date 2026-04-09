'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import {
  Layers,
  Plus,
  Trash2,
  Loader2,
  Download,
  RotateCcw,
  X,
  ChevronRight,
  FileText,
  CheckCircle,
  AlertCircle,
  Clock,
  Package
} from 'lucide-react';
import MainLayout from '@/components/layout/MainLayout';
import Card from '@/components/ui/Card';
import Input from '@/components/ui/Input';
import Button from '@/components/ui/Button';
import Badge from '@/components/ui/Badge';
import { useToast } from '@/components/ui/ToastContainer';
import { batchApi, BatchJob, BatchTask, CreateBatchJobRequest, MembershipTier } from '@/types/api';
import { useAuth } from '@/hooks/useAuth';

// 平台选项
const PLATFORMS = [
  { value: 'wechat', label: '微信公众号', icon: '📱' },
  { value: 'zhihu', label: '知乎', icon: '💡' },
  { value: 'xiaohongshu', label: '小红书', icon: '📕' },
  { value: 'toutiao', label: '今日头条', icon: '📰' },
];

// 状态映射
const STATUS_MAP: Record<string, { label: string; color: string; icon: React.ReactNode }> = {
  pending: { label: '等待中', color: 'gray', icon: <Clock size={16} /> },
  running: { label: '进行中', color: 'blue', icon: <Loader2 size={16} className="animate-spin" /> },
  completed: { label: '已完成', color: 'green', icon: <CheckCircle size={16} /> },
  failed: { label: '失败', color: 'red', icon: <AlertCircle size={16} /> },
  partial: { label: '部分完成', color: 'yellow', icon: <AlertCircle size={16} /> },
};

// 任务状态映射
const TASK_STATUS_MAP: Record<string, { label: string; color: string }> = {
  pending: { label: '等待中', color: 'gray' },
  running: { label: '进行中', color: 'blue' },
  completed: { label: '已完成', color: 'green' },
  failed: { label: '失败', color: 'red' },
};

// 会员限制配置
const BATCH_LIMITS: Record<MembershipTier, { jobsPerMonth: number; maxTopics: number }> = {
  free: { jobsPerMonth: 3, maxTopics: 5 },
  pro: { jobsPerMonth: 10, maxTopics: 20 },
  ultra: { jobsPerMonth: Infinity, maxTopics: 50 },
  superuser: { jobsPerMonth: Infinity, maxTopics: 50 },
};

export default function BatchPage() {
  const router = useRouter();
  const { status, isAuthenticated, membershipTier, profileResolved } = useAuth();
  const { showSuccess, showError } = useToast();
  const signInHref = '/auth/signin?callbackUrl=%2Fbatch';

  const authResolved = status !== 'loading';
  const tierResolved = !isAuthenticated || profileResolved;

  const [jobs, setJobs] = useState<BatchJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [pageError, setPageError] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [selectedJob, setSelectedJob] = useState<BatchJob | null>(null);
  const [jobTasks, setJobTasks] = useState<BatchTask[]>([]);
  const [showDetailDrawer, setShowDetailDrawer] = useState(false);

  // 创建表单状态
  const [formData, setFormData] = useState<CreateBatchJobRequest>({
    name: '',
    topics: [],
    platform: 'wechat',
    concurrency: 3,
    generate_images: false,
  });
  const [topicsText, setTopicsText] = useState('');
  const [creating, setCreating] = useState(false);
  const [downloading, setDownloading] = useState<string | null>(null);
  const [retrying, setRetrying] = useState<string | null>(null);
  const [cancelling, setCancelling] = useState<string | null>(null);

  const limits = BATCH_LIMITS[membershipTier] || BATCH_LIMITS.free;
  const hasBatchAccess = membershipTier !== 'free';

  // 加载任务列表
  const loadJobs = useCallback(async () => {
    if (!isAuthenticated || !tierResolved || !hasBatchAccess) return;
    setLoading(true);
    try {
      const response = await batchApi.getJobs();
      setJobs(response.jobs);
    } catch (error) {
      console.error('Failed to load batch jobs:', error);
      const message = error instanceof Error ? error.message : '加载批量任务失败，请重试';
      setPageError(message);
      showError(message);
    } finally {
      setLoading(false);
    }
  }, [hasBatchAccess, isAuthenticated, showError, tierResolved]);

  useEffect(() => {
    if (status === 'authenticated' && tierResolved) {
      if (!hasBatchAccess) {
        setJobs([]);
        setJobTasks([]);
        setSelectedJob(null);
        setShowDetailDrawer(false);
        setPageError(null);
        setLoading(false);
        return;
      }
      setPageError(null);
      loadJobs();
    } else if (status === 'unauthenticated') {
      setJobs([]);
      setJobTasks([]);
      setSelectedJob(null);
      setShowDetailDrawer(false);
      setPageError(null);
      setLoading(false);
    } else {
      setLoading(true);
    }
  }, [status, loadJobs, tierResolved, hasBatchAccess]);

  useEffect(() => {
    if (status !== 'unauthenticated') {
      return;
    }
    router.replace(signInHref);
  }, [router, signInHref, status]);

  // 轮询刷新进行中的任务
  useEffect(() => {
    const hasRunningJobs = jobs.some(job => job.status === 'running');
    if (!hasRunningJobs) return;

    const interval = setInterval(() => {
      loadJobs();
    }, 5000);

    return () => clearInterval(interval);
  }, [jobs, loadJobs]);

  // 处理主题文本变化
  const handleTopicsChange = (text: string) => {
    setTopicsText(text);
    const topics = text
      .split('\n')
      .map(t => t.trim())
      .filter(t => t.length > 0);
    setFormData(prev => ({ ...prev, topics }));
  };

  // 创建批量任务
  const handleCreateJob = async () => {
    if (!formData.name.trim()) {
      showError('请输入任务名称');
      return;
    }
    if (formData.topics.length === 0) {
      showError('请输入至少一个主题');
      return;
    }
    if (formData.topics.length > limits.maxTopics) {
      showError(`每批最多 ${limits.maxTopics} 个主题`);
      return;
    }

    setCreating(true);
    try {
      await batchApi.createJob(formData);
      showSuccess('批量任务创建成功');
      setShowCreateModal(false);
      setFormData({
        name: '',
        topics: [],
        platform: 'wechat',
        concurrency: 3,
        generate_images: false,
      });
      setTopicsText('');
      await loadJobs();
    } catch (error) {
      console.error('Failed to create batch job:', error);
      showError(error instanceof Error ? error.message : '创建批量任务失败');
    } finally {
      setCreating(false);
    }
  };

  // 查看任务详情
  const handleViewDetail = async (job: BatchJob) => {
    setSelectedJob(job);
    setShowDetailDrawer(true);
    try {
      const response = await batchApi.getJob(job.id);
      setJobTasks(response.tasks);
    } catch (error) {
      console.error('Failed to load job details:', error);
      showError(error instanceof Error ? error.message : '加载任务详情失败');
    }
  };

  // 重试失败任务
  const handleRetry = async (jobId: string) => {
    setRetrying(jobId);
    try {
      const result = await batchApi.retryJob(jobId);
      showSuccess(`已重试 ${result.retried_count} 个任务`);
      await loadJobs();
      if (selectedJob?.id === jobId) {
        const response = await batchApi.getJob(jobId);
        setSelectedJob(response.job);
        setJobTasks(response.tasks);
      }
    } catch (error) {
      console.error('Failed to retry job:', error);
      showError(error instanceof Error ? error.message : '重试失败');
    } finally {
      setRetrying(null);
    }
  };

  // 取消任务
  const handleCancel = async (jobId: string) => {
    if (!confirm('确定要取消这个任务吗？')) return;

    setCancelling(jobId);
    try {
      await batchApi.cancelJob(jobId);
      showSuccess('任务已取消');
      await loadJobs();
    } catch (error) {
      console.error('Failed to cancel job:', error);
      showError(error instanceof Error ? error.message : '取消任务失败');
    } finally {
      setCancelling(null);
    }
  };

  // 下载ZIP
  const handleDownload = async (jobId: string, jobName: string) => {
    setDownloading(jobId);
    try {
      const blob = await batchApi.downloadZip(jobId);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${jobName}.zip`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      showSuccess('下载开始');
    } catch (error) {
      console.error('Failed to download ZIP:', error);
      showError(error instanceof Error ? error.message : '下载失败');
    } finally {
      setDownloading(null);
    }
  };

  const handleRetryLoad = async () => {
    setPageError(null);
    await loadJobs();
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

  // 获取状态显示
  const getStatusDisplay = (status: string) => {
    const config = STATUS_MAP[status] || STATUS_MAP.pending;
    return (
      <Badge variant={config.color as any} className="flex items-center gap-1">
        {config.icon}
        {config.label}
      </Badge>
    );
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

  if (tierResolved && !hasBatchAccess) {
    return (
      <MainLayout>
        <div className="max-w-[1376px] mx-auto">
          <div className="flex items-center gap-3 mb-8">
            <span className="text-[32px]">📦</span>
            <div>
              <h1 className="font-heading text-[32px] font-semibold text-text-primary">
                批量生成
              </h1>
              <p className="font-body text-base text-text-secondary mt-1">
                一次性生成多篇文章，提升内容生产效率
              </p>
            </div>
          </div>

          <Card padding="lg" className="text-center py-16">
            <Package size={64} className="text-text-tertiary mx-auto mb-4" />
            <h3 className="text-lg font-medium text-text-primary mb-2">Pro会员专属功能</h3>
            <p className="text-text-secondary mb-6 max-w-md mx-auto">
              批量生成是 Pro 及以上会员的专属功能。升级会员即可批量创建写作任务，提升内容生产效率。
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
            <span className="text-[32px]">📦</span>
            <div>
              <h1 className="font-heading text-[32px] font-semibold text-text-primary">
                批量生成
              </h1>
              <p className="font-body text-base text-text-secondary mt-1">
                一次性生成多篇文章，提升内容生产效率
              </p>
            </div>
          </div>
          <Button
            variant="primary"
            onClick={() => setShowCreateModal(true)}
            className="flex items-center gap-2"
          >
            <Plus size={18} />
            新建批量任务
          </Button>
        </div>

        {/* 任务列表 */}
        {pageError && jobs.length === 0 ? (
          <Card padding="lg" className="text-center py-16">
            <AlertCircle size={64} className="text-red-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-text-primary mb-2">加载批量任务失败</h3>
            <p className="text-text-secondary mb-6">{pageError}</p>
            <Button variant="primary" onClick={handleRetryLoad}>
              重新加载
            </Button>
          </Card>
        ) : jobs.length === 0 ? (
          <Card padding="lg" className="text-center py-16">
            <Package size={64} className="text-text-tertiary mx-auto mb-4" />
            <h3 className="text-lg font-medium text-text-primary mb-2">还没有批量任务</h3>
            <p className="text-text-secondary mb-6">创建您的第一个批量生成任务，一次性生成多篇文章</p>
            <Button variant="primary" onClick={() => setShowCreateModal(true)}>
              <Plus size={18} className="mr-2" />
              新建批量任务
            </Button>
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {jobs.map((job) => (
              <Card key={job.id} padding="lg" className="hover:shadow-lg transition-shadow">
                <div className="flex items-start justify-between mb-4">
                  <div className="flex-1 min-w-0">
                    <h3 className="font-medium text-text-primary truncate" title={job.name}>
                      {job.name}
                    </h3>
                    <p className="text-sm text-text-tertiary mt-1">
                      {formatDate(job.created_at)}
                    </p>
                  </div>
                  {getStatusDisplay(job.status)}
                </div>

                {/* 进度条 */}
                <div className="mb-4">
                  <div className="flex justify-between text-sm mb-2">
                    <span className="text-text-secondary">进度</span>
                    <span className="text-text-primary font-medium">{job.progress}%</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-primary rounded-full h-2 transition-all duration-300"
                      style={{ width: `${job.progress}%` }}
                    />
                  </div>
                  <div className="flex justify-between text-xs text-text-tertiary mt-2">
                    <span>成功: {job.completed_count}</span>
                    <span>失败: {job.failed_count}</span>
                    <span>总计: {job.total_count}</span>
                  </div>
                </div>

                {/* 操作按钮 */}
                <div className="flex gap-2">
                  <Button
                    variant="secondary"
                    size="sm"
                    className="flex-1"
                    onClick={() => handleViewDetail(job)}
                  >
                    查看详情
                  </Button>
                  {job.status === 'completed' && (
                    <Button
                      variant="primary"
                      size="sm"
                      onClick={() => handleDownload(job.id, job.name)}
                      disabled={!!downloading || !job.zip_url}
                      className="flex items-center gap-1"
                    >
                      {downloading === job.id ? (
                        <Loader2 size={16} className="animate-spin" />
                      ) : (
                        <Download size={16} />
                      )}
                      下载
                    </Button>
                  )}
                  {job.status === 'partial' && (
                    <>
                      <Button
                        variant="primary"
                        size="sm"
                        onClick={() => handleDownload(job.id, job.name)}
                        disabled={!!downloading || !job.zip_url}
                        className="flex items-center gap-1"
                      >
                        {downloading === job.id ? (
                          <Loader2 size={16} className="animate-spin" />
                        ) : (
                          <Download size={16} />
                        )}
                        下载
                      </Button>
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => handleRetry(job.id)}
                        disabled={!!retrying}
                        className="flex items-center gap-1"
                      >
                        {retrying === job.id ? (
                          <Loader2 size={16} className="animate-spin" />
                        ) : (
                          <RotateCcw size={16} />
                        )}
                        重试
                      </Button>
                    </>
                  )}
                  {job.status === 'failed' && (
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => handleRetry(job.id)}
                      disabled={!!retrying}
                      className="flex items-center gap-1"
                    >
                      {retrying === job.id ? (
                        <Loader2 size={16} className="animate-spin" />
                      ) : (
                        <RotateCcw size={16} />
                      )}
                      重试
                    </Button>
                  )}
                  {job.status === 'running' && (
                    <button
                      onClick={() => handleCancel(job.id)}
                      disabled={!!cancelling}
                      className="inline-flex items-center justify-center gap-1 h-10 px-4 text-sm font-semibold rounded-md bg-red-50 text-red-600 hover:bg-red-100 transition-colors disabled:opacity-50"
                    >
                      {cancelling === job.id ? (
                        <Loader2 size={16} className="animate-spin" />
                      ) : (
                        <X size={16} />
                      )}
                      取消
                    </button>
                  )}
                </div>
              </Card>
            ))}
          </div>
        )}

        {/* 创建任务 Modal */}
        {showCreateModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center">
            <div
              className="absolute inset-0 bg-black/50 backdrop-blur-sm"
              onClick={() => setShowCreateModal(false)}
            />
            <div className="relative bg-white rounded-xl shadow-xl w-full max-w-2xl max-h-[90vh] overflow-hidden animate-in fade-in zoom-in-95 duration-200">
              <div className="flex items-center justify-between p-6 border-b border-border">
                <h2 className="text-xl font-semibold text-text-primary">新建批量任务</h2>
                <button
                  onClick={() => setShowCreateModal(false)}
                  className="text-text-secondary hover:text-text-primary transition-colors"
                >
                  <X size={24} />
                </button>
              </div>

              <div className="p-6 overflow-y-auto max-h-[calc(90vh-140px)]">
                <div className="space-y-6">
                  {/* 任务名称 */}
                  <div>
                    <label className="block text-sm font-medium text-text-primary mb-2">
                      任务名称 <span className="text-red-500">*</span>
                    </label>
                    <Input
                      value={formData.name}
                      onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                      placeholder="例如：科技周报"
                    />
                  </div>

                  {/* 主题列表 */}
                  <div>
                    <label className="block text-sm font-medium text-text-primary mb-2">
                      主题列表 <span className="text-red-500">*</span>
                      <span className="text-text-tertiary font-normal ml-2">
                        (每行一个主题，最多 {limits.maxTopics} 个)
                      </span>
                    </label>
                    <textarea
                      value={topicsText}
                      onChange={(e) => handleTopicsChange(e.target.value)}
                      placeholder="输入多个主题，每行一个&#10;例如：&#10;人工智能发展趋势&#10;新能源汽车技术&#10;区块链应用案例"
                      rows={6}
                      className="w-full px-4 py-3 bg-surface border-[1.5px] border-border rounded-xl font-body text-[15px] text-text-primary focus:border-primary focus:outline-none focus:ring-3 focus:ring-primary/10 transition-all resize-none"
                    />
                    <div className="flex justify-between text-sm mt-2">
                      <span className="text-text-tertiary">
                        已输入 {formData.topics.length} 个主题
                      </span>
                      {formData.topics.length > limits.maxTopics && (
                        <span className="text-red-500">
                          超出限制 ({limits.maxTopics})
                        </span>
                      )}
                    </div>
                  </div>

                  {/* 平台选择 */}
                  <div>
                    <label className="block text-sm font-medium text-text-primary mb-2">
                      输出平台
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

                  {/* 并发数 */}
                  <div>
                    <label className="block text-sm font-medium text-text-primary mb-2">
                      并发数: {formData.concurrency}
                    </label>
                    <input
                      type="range"
                      min={1}
                      max={5}
                      value={formData.concurrency}
                      onChange={(e) => setFormData(prev => ({ ...prev, concurrency: parseInt(e.target.value) }))}
                      className="w-full"
                    />
                    <div className="flex justify-between text-xs text-text-tertiary mt-1">
                      <span>1</span>
                      <span>3</span>
                      <span>5</span>
                    </div>
                  </div>

                  {/* 生成图片 */}
                  <div className="flex items-center gap-3">
                    <input
                      type="checkbox"
                      id="generate_images"
                      checked={formData.generate_images}
                      onChange={(e) => setFormData(prev => ({ ...prev, generate_images: e.target.checked }))}
                      className="w-5 h-5 rounded border-border text-primary focus:ring-primary"
                    />
                    <label htmlFor="generate_images" className="text-text-primary">
                      自动生成配图
                    </label>
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
                  onClick={handleCreateJob}
                  disabled={creating || !formData.name.trim() || formData.topics.length === 0 || formData.topics.length > limits.maxTopics}
                  className="flex-1"
                >
                  {creating ? (
                    <>
                      <Loader2 size={18} className="animate-spin mr-2" />
                      创建中...
                    </>
                  ) : (
                    <>
                      <Plus size={18} className="mr-2" />
                      创建任务
                    </>
                  )}
                </Button>
              </div>
            </div>
          </div>
        )}

        {/* 任务详情 Drawer */}
        {showDetailDrawer && selectedJob && (
          <div className="fixed inset-0 z-50 flex justify-end">
            <div
              className="absolute inset-0 bg-black/50 backdrop-blur-sm"
              onClick={() => setShowDetailDrawer(false)}
            />
            <div className="relative bg-white w-full max-w-lg h-full overflow-hidden animate-in slide-in-from-right duration-200">
              <div className="flex items-center justify-between p-6 border-b border-border">
                <div>
                  <h2 className="text-xl font-semibold text-text-primary truncate max-w-[300px]">
                    {selectedJob.name}
                  </h2>
                  <p className="text-sm text-text-tertiary mt-1">
                    {formatDate(selectedJob.created_at)}
                  </p>
                </div>
                <button
                  onClick={() => setShowDetailDrawer(false)}
                  className="text-text-secondary hover:text-text-primary transition-colors"
                >
                  <X size={24} />
                </button>
              </div>

              <div className="p-6 overflow-y-auto h-[calc(100vh-200px)]">
                {/* 任务概览 */}
                <div className="mb-6">
                  <div className="flex items-center justify-between mb-4">
                    {getStatusDisplay(selectedJob.status)}
                    <span className="text-text-primary font-medium">{selectedJob.progress}%</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2 mb-4">
                    <div
                      className="bg-primary rounded-full h-2 transition-all duration-300"
                      style={{ width: `${selectedJob.progress}%` }}
                    />
                  </div>
                  <div className="grid grid-cols-3 gap-4 text-center">
                    <div className="p-3 bg-green-50 rounded-lg">
                      <div className="text-2xl font-semibold text-green-600">{selectedJob.completed_count}</div>
                      <div className="text-xs text-green-700">成功</div>
                    </div>
                    <div className="p-3 bg-red-50 rounded-lg">
                      <div className="text-2xl font-semibold text-red-600">{selectedJob.failed_count}</div>
                      <div className="text-xs text-red-700">失败</div>
                    </div>
                    <div className="p-3 bg-gray-50 rounded-lg">
                      <div className="text-2xl font-semibold text-gray-600">{selectedJob.total_count}</div>
                      <div className="text-xs text-gray-700">总计</div>
                    </div>
                  </div>
                </div>

                {/* 任务列表 */}
                <h3 className="font-medium text-text-primary mb-4">主题生成状态</h3>
                <div className="space-y-3">
                  {jobTasks.length === 0 ? (
                    <div className="text-center py-8">
                      <Loader2 size={32} className="animate-spin text-primary mx-auto mb-2" />
                      <p className="text-text-secondary">加载中...</p>
                    </div>
                  ) : (
                    jobTasks.map((task) => {
                      const statusConfig = TASK_STATUS_MAP[task.status] || TASK_STATUS_MAP.pending;
                      return (
                        <div
                          key={task.id}
                          className="p-4 border border-border rounded-xl hover:bg-gray-50 transition-colors"
                        >
                          <div className="flex items-start justify-between">
                            <div className="flex-1 min-w-0">
                              <p className="text-text-primary font-medium truncate" title={task.topic}>
                                {task.topic}
                              </p>
                              {task.error_message && (
                                <p className="text-sm text-red-500 mt-1">{task.error_message}</p>
                              )}
                            </div>
                            <Badge variant={statusConfig.color as any} className="ml-2 flex-shrink-0">
                              {statusConfig.label}
                            </Badge>
                          </div>
                          {task.article_id && (
                            <button
                              onClick={() => router.push(`/history/${task.article_id}`)}
                              className="mt-2 text-sm text-primary hover:underline flex items-center gap-1"
                            >
                              <FileText size={14} />
                              查看文章
                            </button>
                          )}
                        </div>
                      );
                    })
                  )}
                </div>
              </div>

              {/* 底部操作 */}
              <div className="absolute bottom-0 left-0 right-0 p-6 border-t border-border bg-white">
                <div className="flex gap-3">
                  {(selectedJob.status === 'completed' || selectedJob.status === 'partial') && selectedJob.zip_url && (
                    <Button
                      variant="primary"
                      onClick={() => handleDownload(selectedJob.id, selectedJob.name)}
                      disabled={!!downloading}
                      className="flex-1"
                    >
                      {downloading === selectedJob.id ? (
                        <Loader2 size={18} className="animate-spin mr-2" />
                      ) : (
                        <Download size={18} className="mr-2" />
                      )}
                      下载全部
                    </Button>
                  )}
                  {(selectedJob.status === 'failed' || selectedJob.status === 'partial') && (
                    <Button
                      variant="secondary"
                      onClick={() => handleRetry(selectedJob.id)}
                      disabled={!!retrying}
                      className="flex-1"
                    >
                      {retrying === selectedJob.id ? (
                        <Loader2 size={18} className="animate-spin mr-2" />
                      ) : (
                        <RotateCcw size={18} className="mr-2" />
                      )}
                      重试失败
                    </Button>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </MainLayout>
  );
}
