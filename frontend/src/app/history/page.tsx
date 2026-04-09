'use client';

import { useState, useEffect, useMemo, useCallback } from 'react';
import MainLayout from '@/components/layout/MainLayout';
import Card from '@/components/ui/Card';
import Button from '@/components/ui/Button';
import Badge from '@/components/ui/Badge';
import { useToast } from '@/components/ui/ToastContainer';
import { SEOPanel } from '@/components/writer/SEOPanel';
import PublishModal from '@/components/writer/PublishModal';
import dynamic from 'next/dynamic';
import { historyApi, type Article } from '@/types/api';
import {
  FileText,
  Download,
  Trash2,
  Search,
  Filter,
  Loader2,
  Calendar,
  Clock,
  Type,
  ExternalLink,
  ChevronRight,
  Edit3,
  BarChart3,
  Sparkles,
  Zap,
  Cpu,
  Globe,
  Image as ImageIcon,
  Send
} from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';

// 动态导入重型组件
const NovelEditor = dynamic(() => import('@/components/ui/NovelEditor'), {
  ssr: false,
  loading: () => <div className="h-40 flex items-center justify-center text-text-tertiary">正在加载预览引擎...</div>
});

const SplitEditor = dynamic(() => import('@/components/writer/SplitEditor').then(mod => mod.SplitEditor), {
  ssr: false,
  loading: () => (
    <div className="flex items-center justify-center py-20">
      <Loader2 className="animate-spin text-primary" size={48} />
    </div>
  )
});

export default function HistoryPage() {
  const router = useRouter();
  const { status, isAuthenticated } = useAuth();
  const { showError, showSuccess } = useToast();
  const signInHref = '/auth/signin?callbackUrl=%2Fhistory';
  const [articles, setArticles] = useState<Article[]>([]);
  const [loading, setLoading] = useState(true);
  const [pageError, setPageError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [previewArticle, setPreviewArticle] = useState<Article | null>(null);
  const [editArticle, setEditArticle] = useState<Article | null>(null);
  const [total, setTotal] = useState(0);
  const [publishArticle, setPublishArticle] = useState<Article | null>(null);

  const loadArticles = useCallback(async () => {
    if (!isAuthenticated) return;
    setLoading(true);
    try {
      setPageError(null);
      const pageSize = 50;
      const firstPage = await historyApi.getArticles(1, pageSize);
      const collectedArticles = [...firstPage.items];
      const totalCount = firstPage.total ?? firstPage.items.length;
      const totalPages = Math.max(1, Math.ceil(totalCount / pageSize));

      setArticles(collectedArticles);
      setTotal(totalCount);

      if (totalPages > 1) {
        const remainingPages = await Promise.allSettled(
          Array.from({ length: totalPages - 1 }, (_, index) =>
            historyApi.getArticles(index + 2, pageSize)
          )
        );

        let hasPartialFailure = false;
        remainingPages.forEach((result) => {
          if (result.status === 'fulfilled') {
            collectedArticles.push(...result.value.items);
            return;
          }

          hasPartialFailure = true;
        });

        if (hasPartialFailure) {
          showError('部分历史记录加载失败，已展示可用内容');
        }
      }

      setArticles(collectedArticles);
      setTotal(totalCount);
    } catch (error) {
      console.error('加载文章失败:', error);
      setArticles([]);
      setTotal(0);
      setPageError('加载历史记录失败，请检查网络后重试');
      showError('加载历史记录失败，请稍后重试');
    } finally {
      setLoading(false);
    }
  }, [isAuthenticated, showError]);

  useEffect(() => {
    if (status === 'authenticated') {
      loadArticles();
      return;
    }

    if (status === 'unauthenticated') {
      setArticles([]);
      setPreviewArticle(null);
      setEditArticle(null);
      setTotal(0);
      setLoading(false);
      return;
    }

    setLoading(true);
  }, [loadArticles, status]);

  useEffect(() => {
    if (status !== 'unauthenticated') {
      return;
    }

    router.replace(signInHref);
  }, [router, signInHref, status]);

  // 统计数据
  const stats = useMemo(() => {
    const totalWords = articles.reduce((acc, art) => acc + (art.content?.length || 0), 0);
    const completedCount = articles.filter(a => a.status === 'published').length;
    return {
      total: total,
      words: totalWords,
      completed: completedCount,
      successRate: total > 0 ? Math.round((completedCount / total) * 100) : 0
    };
  }, [articles, total]);

  // 筛选文章
  const filteredArticles = useMemo(() => {
    return articles.filter(article => {
      const matchesSearch = (article.topic || article.title || '').toLowerCase().includes(searchTerm.toLowerCase());
      const matchesStatus = filterStatus === 'all' || article.status === filterStatus;
      return matchesSearch && matchesStatus;
    });
  }, [articles, searchTerm, filterStatus]);

  // 删除文章
  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm('确定要删除这篇文章吗？')) return;
    
    try {
      await historyApi.deleteArticle(id);
      setArticles(prev => prev.filter(a => a.id !== id));
      setTotal(prev => prev - 1);
    } catch (error) {
      console.error('删除失败:', error);
      showError('删除失败，请重试');
    }
  };

  // 下载Markdown
  const handleDownload = (article: Article, e: React.MouseEvent) => {
    e.stopPropagation();
    const isHtml = article.content?.trim().startsWith('<');
    const blob = new Blob([article.content || ''], { type: isHtml ? 'text/html' : 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${article.title || article.topic || 'article'}.${isHtml ? 'html' : 'md'}`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleEdit = (article: Article, e: React.MouseEvent) => {
    e.stopPropagation();
    setEditArticle(article);
  };

  const handleEditSave = async (content: string) => {
    if (!editArticle) return;
    try {
      await historyApi.updateArticle(editArticle.id, content);
      // 更新本地列表中的内容
      setArticles(prev => prev.map(a => a.id === editArticle.id ? { ...a, content } : a));
      setEditArticle(null);
    } catch (error) {
      console.error('保存失败:', error);
      showError('保存失败，请重试');
    }
  };

  // 获取状态标签
  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'published':
        return <Badge variant="success">已发布</Badge>;
      case 'draft':
        return <Badge variant="primary">草稿</Badge>;
      case 'archived':
        return <Badge variant="default">已归档</Badge>;
      default:
        return <Badge variant="default">{status}</Badge>;
    }
  };

  return (
    <MainLayout>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 animate-in fade-in duration-500">
        {status === 'unauthenticated' ? (
          <div className="flex flex-col items-center justify-center py-20 bg-white rounded-3xl shadow-standard">
            <Loader2 className="animate-spin text-primary mb-4" size={48} />
            <p className="text-text-secondary font-medium">正在跳转到登录...</p>
          </div>
        ) : (
          <>
        {/* Page Header */}
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-10">
          <div>
            <div className="flex items-center gap-4 mb-2">
              <div className="w-12 h-12 bg-primary/10 rounded-2xl flex items-center justify-center">
                <FileText className="text-primary" size={28} />
              </div>
              <h1 className="font-heading text-4xl font-bold text-text-primary tracking-tight">
                创作中心 <span className="text-primary/40">/</span> 历史记录
              </h1>
            </div>
            <p className="font-body text-lg text-text-secondary max-w-2xl">
              在这里管理您的所有创作灵感。您可以预览、编辑或导出您的文章，让每一份文字都发挥最大的价值。
            </p>
          </div>
          
          <div className="flex gap-3">
             <Button variant="primary" onClick={() => router.push('/writer')}>
                开始新创作
             </Button>
          </div>
        </div>

        {/* Stats Section */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-10">
          {[
            { label: '总创作数', value: stats.total, icon: <BarChart3 className="text-primary" />, suffix: '篇' },
            { label: '累计字数', value: stats.words.toLocaleString(), icon: <Type className="text-cta" />, suffix: '字' },
            { label: '已发布', value: stats.completed, icon: <Sparkles className="text-success" />, suffix: '篇' },
            { label: '产出效率', value: stats.successRate, icon: <Zap className="text-info" />, suffix: '%' },
          ].map((stat, i) => (
            <Card key={i} padding="lg" className="border-none shadow-standard bg-white/50 backdrop-blur-sm hover:shadow-strong transition-all duration-300">
              <div className="flex items-center gap-4">
                <div className="p-3 bg-white rounded-xl shadow-sm">
                  {stat.icon}
                </div>
                <div>
                  <p className="text-sm font-medium text-text-secondary">{stat.label}</p>
                  <p
                    className="text-2xl font-bold text-text-primary"
                    data-testid={stat.label === '总创作数' ? 'history-stats-total' : undefined}
                  >
                    {stat.value} <span className="text-sm font-normal text-text-tertiary">{stat.suffix}</span>
                  </p>
                </div>
              </div>
            </Card>
          ))}
        </div>

        {/* Search and Filters */}
        <div className="bg-white p-4 rounded-2xl shadow-standard mb-8 flex flex-col md:flex-row gap-4 items-center">
          <div className="relative flex-1 w-full">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-text-tertiary" size={20} />
            <input
              type="text"
              placeholder="通过标题、主题或关键词搜索文章..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full h-12 pl-12 pr-4 bg-bg border-none rounded-xl font-body text-[15px] text-text-primary placeholder:text-text-tertiary focus:ring-2 focus:ring-primary/20 transition-all"
            />
          </div>

          <div className="flex gap-3 w-full md:w-auto">
            <div className="flex items-center gap-2 bg-bg px-4 py-2 rounded-xl border border-transparent focus-within:border-primary/20 transition-all">
              <Filter size={18} className="text-text-secondary" />
              <select
                value={filterStatus}
                onChange={(e) => setFilterStatus(e.target.value)}
                className="bg-transparent border-none font-body text-sm text-text-primary focus:ring-0 cursor-pointer"
              >
                <option value="all">全部状态</option>
                <option value="published">已发布</option>
                <option value="draft">草稿箱</option>
              </select>
            </div>
            
            <Button variant="secondary" onClick={() => {setSearchTerm(''); setFilterStatus('all');}}>
              重置
            </Button>
          </div>
        </div>

        {/* Article List */}
        <div className="space-y-4">
          {loading ? (
            <div className="flex flex-col items-center justify-center py-20 bg-white rounded-3xl shadow-standard">
              <Loader2 className="animate-spin text-primary mb-4" size={48} />
              <p className="text-text-secondary font-medium">正在调取您的创作档案...</p>
            </div>
          ) : pageError ? (
            <div className="text-center py-20 bg-white rounded-3xl shadow-standard border border-red-100">
              <div className="w-16 h-16 mx-auto mb-6 rounded-2xl bg-red-50 flex items-center justify-center">
                <FileText className="text-red-500" size={30} />
              </div>
              <h3 className="font-heading text-2xl font-bold text-text-primary mb-3">
                历史记录暂时加载失败
              </h3>
              <p className="font-body text-text-secondary max-w-md mx-auto mb-8">
                {pageError}
              </p>
              <div className="flex items-center justify-center gap-3">
                <Button variant="secondary" onClick={() => router.push('/writer')}>
                  去创作中心
                </Button>
                <Button variant="primary" onClick={() => loadArticles()}>
                  重新加载
                </Button>
              </div>
            </div>
          ) : filteredArticles.length === 0 ? (
            <div className="text-center py-20 bg-white rounded-3xl shadow-standard border-2 border-dashed border-border">
              <div className="text-7xl mb-6">🏜️</div>
              <h3 className="font-heading text-2xl font-bold text-text-primary mb-3">
                {searchTerm ? '未找到相关结果' : '创作荒漠'}
              </h3>
              <p className="font-body text-text-secondary max-w-sm mx-auto mb-8">
                {searchTerm ? '请尝试更换搜索词，或者重置筛选条件。' : '您还没有开始任何创作。快去写下您的第一篇传世之作吧！'}
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-4">
              {filteredArticles.map(article => {
                const isHtml = article.content?.trim().startsWith('<');
                return (
                  <div 
                    key={article.id}
                    onClick={() => setPreviewArticle(article)}
                    data-testid={`history-article-${article.id}`}
                    className="group relative bg-white rounded-2xl p-5 border border-border/50 shadow-sm hover:shadow-strong hover:border-primary/20 transition-all duration-300 cursor-pointer flex flex-col md:flex-row md:items-center gap-6"
                  >
                    <div className="w-16 h-16 bg-bg rounded-2xl flex items-center justify-center flex-shrink-0 group-hover:scale-110 transition-transform duration-300">
                      {isHtml ? (
                         <div className="relative">
                            <ExternalLink className="text-cta" size={32} />
                            <span className="absolute -top-2 -right-2 text-[10px] bg-cta text-white px-1.5 rounded-full font-bold">HTML</span>
                         </div>
                      ) : (
                         <div className="relative">
                            <FileText className="text-primary" size={32} />
                            <span className="absolute -top-2 -right-2 text-[10px] bg-primary text-white px-1.5 rounded-full font-bold">MD</span>
                         </div>
                      )}
                    </div>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-3 mb-2 flex-wrap">
                        <h3 className="font-heading text-xl font-bold text-text-primary group-hover:text-primary transition-colors line-clamp-1">
                          {article.title || article.topic}
                        </h3>
                        {getStatusBadge(article.status)}
                      </div>
                      
                      <div className="flex items-center gap-4 text-sm text-text-secondary flex-wrap">
                        <div className="flex items-center gap-1.5">
                          <Calendar size={14} />
                          {new Date(article.created_at).toLocaleDateString('zh-CN')}
                        </div>
                        <div className="flex items-center gap-1.5">
                          <Clock size={14} />
                          {new Date(article.created_at).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}
                        </div>
                        <div className="flex items-center gap-1.5">
                          <Type size={14} />
                          {article.content?.length || 0} 字
                        </div>
                      </div>
                      {/* 生成参数 */}
                      {article.metadata && Object.keys(article.metadata).length > 0 && (
                        <div className="flex items-center gap-3 mt-1.5 text-xs text-text-tertiary flex-wrap">
                          {(article.metadata.model_type || article.metadata.model_name) && (
                            <div className="flex items-center gap-1 bg-primary/5 px-2 py-0.5 rounded-full">
                              <Cpu size={12} className="text-primary" />
                              <span>{article.metadata.model_name || article.metadata.model_type}</span>
                            </div>
                          )}
                          {article.metadata.spider_num != null && (
                            <div className="flex items-center gap-1 bg-cta/5 px-2 py-0.5 rounded-full">
                              <Globe size={12} className="text-cta" />
                              <span>{article.metadata.spider_num} 条搜索</span>
                            </div>
                          )}
                          {article.metadata.total_images != null && (
                            <div className="flex items-center gap-1 bg-success/5 px-2 py-0.5 rounded-full">
                              <ImageIcon size={12} className="text-success" />
                              <span>{article.metadata.total_images} 张图片</span>
                            </div>
                          )}
                        </div>
                      )}
                    </div>

                    <div className="flex items-center gap-3 flex-shrink-0">
                      <button
                        onClick={(e) => handleDownload(article, e)}
                        className="w-[44px] h-[44px] flex items-center justify-center rounded-xl border-2 border-primary/30 text-primary hover:border-primary hover:bg-primary/5 transition-all"
                        title="下载文章"
                      >
                        <Download size={24} strokeWidth={2.5} />
                      </button>
                      <button
                        onClick={(e) => handleEdit(article, e)}
                        className="w-[44px] h-[44px] flex items-center justify-center rounded-xl border-2 border-primary/30 text-primary hover:border-primary hover:bg-primary/5 transition-all"
                        title="编辑文章"
                      >
                        <Edit3 size={24} strokeWidth={2.5} />
                      </button>
                      <button
                        onClick={(e) => { e.stopPropagation(); setPublishArticle(article); }}
                        className="w-[44px] h-[44px] flex items-center justify-center rounded-xl border-2 border-cta/30 text-cta hover:border-cta hover:bg-cta/5 transition-all"
                        title="一键发布"
                      >
                        <Send size={24} strokeWidth={2.5} />
                      </button>
                      <button
                        onClick={(e) => handleDelete(article.id, e)}
                        data-testid={`history-article-delete-${article.id}`}
                        className="w-[44px] h-[44px] flex items-center justify-center rounded-xl border-2 border-red-200 text-red-500 hover:border-red-400 hover:bg-red-50 transition-all"
                        title="删除文章"
                      >
                        <Trash2 size={24} strokeWidth={2.5} />
                      </button>
                      <ChevronRight size={24} className="text-text-tertiary" />
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Unified Preview Modal */}
        {previewArticle && (
          <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4 md:p-10 animate-in fade-in duration-300">
            <div className="bg-surface rounded-[32px] w-full max-w-5xl h-full max-h-[90vh] flex flex-col shadow-2xl overflow-hidden animate-in zoom-in-95 duration-300">
              <div className="flex items-center justify-between p-6 md:px-10 border-b border-border bg-white/50">
                <div className="flex items-center gap-4">
                  <div className={`p-2 rounded-xl ${previewArticle.content?.trim().startsWith('<') ? 'bg-cta/10 text-cta' : 'bg-primary/10 text-primary'}`}>
                    <FileText size={24} />
                  </div>
                  <div>
                    <h2 className="font-heading text-2xl font-bold text-text-primary line-clamp-1">
                      {previewArticle.title || previewArticle.topic}
                    </h2>
                    <p className="text-sm text-text-secondary flex items-center gap-2">
                      {new Date(previewArticle.created_at).toLocaleString('zh-CN')} · {previewArticle.content?.length || 0} 字
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <Button variant="secondary" onClick={(e) => handleDownload(previewArticle, e)}>下载</Button>
                  <Button variant="primary" onClick={() => setPreviewArticle(null)}>关闭</Button>
                </div>
              </div>
              
              <div className="flex-1 overflow-y-auto p-6 md:p-10 bg-bg/30">
                <div className="max-w-3xl mx-auto space-y-6">
                  {previewArticle.content?.trim().startsWith('<') ? (
                    <div className="bg-white rounded-2xl shadow-standard overflow-hidden min-h-[600px] border border-border">
                       <iframe
                          srcDoc={previewArticle.content}
                          className="w-full h-[600px] border-none"
                          title="HTML预览"
                       />
                    </div>
                  ) : (
                    <div className="bg-white rounded-2xl shadow-standard p-8 md:p-12 border border-border">
                       <NovelEditor key={previewArticle.id} content={previewArticle.content || ''} readOnly={true} />
                    </div>
                  )}

                  {/* SEO分析面板 */}
                  {previewArticle.content && previewArticle.content.length > 50 && (
                    <SEOPanel
                      content={previewArticle.content}
                      title={previewArticle.title || previewArticle.topic || ''}
                      articleId={previewArticle.id}
                      onApplyTitle={(newTitle) => {
                        setArticles(prev => prev.map(a => a.id === previewArticle.id ? { ...a, title: newTitle } : a));
                        setPreviewArticle(prev => (
                          prev && prev.id === previewArticle.id ? { ...prev, title: newTitle } : prev
                        ));
                      }}
                      onCopyMeta={(description) => {
                        navigator.clipboard.writeText(description);
                        showSuccess('元描述已复制到剪贴板');
                      }}
                    />
                  )}
                </div>
              </div>
              
              <div className="p-6 border-t border-border bg-white flex justify-center gap-4">
                 <p className="text-sm text-text-tertiary">
                    提示：您可以在编辑模式中修改文章内容，或导出为多种格式。
                 </p>
              </div>
            </div>
          </div>
        )}

        {/* Edit Article Modal */}
        {editArticle && (
          <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4 animate-in fade-in duration-300">
            <div className="bg-surface rounded-2xl w-full max-w-[95vw] h-[90vh] flex flex-col shadow-2xl overflow-hidden animate-in zoom-in-95 duration-300">
              <div className="flex items-center justify-between px-6 py-4 border-b border-border bg-white">
                <div className="flex items-center gap-3">
                  <Edit3 size={20} className="text-primary" />
                  <h2 className="font-heading text-lg font-bold text-text-primary line-clamp-1">
                    编辑: {editArticle.title || editArticle.topic}
                  </h2>
                </div>
                <button
                  onClick={() => setEditArticle(null)}
                  className="px-4 py-2 rounded-lg bg-bg-secondary text-text-primary hover:bg-bg-tertiary transition-colors text-sm font-medium"
                >
                  关闭
                </button>
              </div>
              <div className="flex-1 overflow-y-auto p-4">
                <SplitEditor
                  articleId={editArticle.id}
                  initialContent={editArticle.content || ''}
                  onSave={(content) => handleEditSave(content)}
                />
              </div>
            </div>
          </div>
        )}

        {/* Publish Modal */}
        {publishArticle && (
          <PublishModal
            article={publishArticle}
            open={!!publishArticle}
            onClose={() => setPublishArticle(null)}
          />
        )}
          </>
        )}
      </div>
    </MainLayout>
  );
}
