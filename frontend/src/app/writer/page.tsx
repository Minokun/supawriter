'use client';

import { useState, useEffect, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import MainLayout from '@/components/layout/MainLayout';
import { WriterForm } from '@/components/writer/WriterForm';
import { TaskQueue } from '@/components/writer/TaskQueue';
import { TaskProgress } from '@/components/writer/TaskProgress';
import { historyApi } from '@/types/api';
import { Loader2 } from 'lucide-react';
import dynamic from 'next/dynamic';

// 动态导入分屏编辑器，因为它引用了 Monaco 和 Novel
const SplitEditor = dynamic(() => import('@/components/writer/SplitEditor').then(mod => mod.SplitEditor), {
  ssr: false,
  loading: () => (
    <div className="flex flex-col items-center justify-center py-20 bg-white rounded-3xl shadow-standard">
      <Loader2 className="animate-spin text-primary mb-4" size={48} />
      <p className="text-text-secondary font-medium">正在启动智能编辑器...</p>
    </div>
  )
});

type ViewState = 'form' | 'generating' | 'completed' | 'loading';

function WriterContent() {
  const searchParams = useSearchParams();
  const topicParam = searchParams.get('topic');
  const sourceParam = searchParams.get('source');
  const urlsParam = searchParams.get('urls');
  const requirementsParam = searchParams.get('requirements');
  const [view, setView] = useState<ViewState>('form');
  const [activeTaskId, setActiveTaskId] = useState<string | null>(null);
  const [completedArticle, setCompletedArticle] = useState<any>(null);
  const [queueRefresh, setQueueRefresh] = useState(0);
  const [articleLoadError, setArticleLoadError] = useState<string | null>(null);

  // Handle article editing from history
  useEffect(() => {
    const articleId = searchParams.get('articleId');
    const mode = searchParams.get('mode');

    if (articleId && mode === 'edit') {
      loadArticleForEdit(articleId);
    }
  }, [searchParams]);

  const loadArticleForEdit = async (id: string) => {
    setView('loading');
    setArticleLoadError(null);
    try {
      const article = await historyApi.getArticle(id);
      setCompletedArticle(article);
      setView('completed');
    } catch (error) {
      console.error('加载文章失败:', error);
      setCompletedArticle(null);
      setArticleLoadError('历史文章加载失败，请稍后重试或返回重新选择文章。');
      setView('form');
    }
  };

  const handleTaskSubmit = (taskId: string) => {
    setActiveTaskId(taskId);
    setView('generating');
    setQueueRefresh(prev => prev + 1);
  };

  const handleTaskSelect = (taskId: string) => {
    setActiveTaskId(taskId);
    setView('generating');
  };

  const handleGenerationComplete = (article: any) => {
    setCompletedArticle(article);
    setView('completed');
  };

  const handleReset = () => {
    setActiveTaskId(null);
    setCompletedArticle(null);
    setArticleLoadError(null);
    setView('form');
    // Clear URL params if any
    if (typeof window !== 'undefined') {
      window.history.pushState({}, '', '/writer');
    }
  };

  return (
    <>
      {/* Header */}
      <div className="mb-8 animate-in fade-in slide-in-from-top-4 duration-500">
        <div className="flex items-center gap-3 mb-3">
          <span className="text-[28px]">✨</span>
          <h1 className="font-heading text-[28px] font-semibold text-text-primary">
            文章创作
          </h1>
        </div>
        <p className="font-body text-base text-text-secondary">
          一键生成高质量文章、博客、营销文案
        </p>
      </div>

      {/* Content */}
      {view === 'loading' && (
        <div className="flex flex-col items-center justify-center py-20 animate-in fade-in duration-300">
          <Loader2 className="animate-spin text-primary mb-4" size={48} />
          <p className="text-text-secondary">加载文章中...</p>
        </div>
      )}

      {view === 'form' && (
        articleLoadError ? (
          <div className="max-w-2xl mx-auto bg-white rounded-3xl shadow-standard p-10 text-center animate-in fade-in zoom-in-95 duration-300">
            <div className="w-16 h-16 mx-auto mb-6 rounded-2xl bg-red-50 text-red-500 flex items-center justify-center text-2xl">
              !
            </div>
            <h2 className="text-2xl font-semibold text-text-primary mb-3">文章加载失败</h2>
            <p className="text-text-secondary mb-8">{articleLoadError}</p>
            <div className="flex items-center justify-center gap-3">
              <button
                onClick={handleReset}
                className="px-4 py-3 rounded-xl border border-border text-text-primary hover:border-primary/40 hover:text-primary transition-colors"
              >
                返回创作中心
              </button>
              <button
                onClick={() => {
                  const articleId = searchParams.get('articleId');
                  if (articleId) {
                    loadArticleForEdit(articleId);
                  }
                }}
                className="px-4 py-3 rounded-xl bg-primary text-white hover:opacity-90 transition-opacity"
              >
                重新加载文章
              </button>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 animate-in fade-in zoom-in-95 duration-300">
            <WriterForm
              onSubmit={handleTaskSubmit}
              initialTopic={topicParam || undefined}
              initialSource={sourceParam || undefined}
              initialCustomStyle={requirementsParam || undefined}
              initialExtraUrls={urlsParam || undefined}
            />
            <TaskQueue
              onTaskSelect={handleTaskSelect}
              refreshTrigger={queueRefresh}
            />
          </div>
        )
      )}

      {view === 'generating' && activeTaskId && (
        <div className="max-w-4xl mx-auto animate-in fade-in slide-in-from-bottom-8 duration-300">
          <div className="mb-4">
            <button
              onClick={handleReset}
              className="text-sm text-text-secondary hover:text-primary transition-all duration-200 hover:translate-x-[-4px]"
            >
              ← 返回
            </button>
          </div>
          <TaskProgress
            taskId={activeTaskId}
            onComplete={handleGenerationComplete}
          />
        </div>
      )}

      {view === 'completed' && completedArticle && (
        <div className="max-w-6xl mx-auto animate-in fade-in slide-in-from-bottom-8 duration-300">
          <div className="mb-4 flex items-center justify-between">
            <button
              onClick={handleReset}
              className="text-sm text-text-secondary hover:text-primary transition-all duration-200 hover:translate-x-[-4px]"
            >
              ← 返回
            </button>
            <h2 className="text-xl font-semibold text-text-primary line-clamp-1 max-w-md">
              {completedArticle.title || completedArticle.topic}
            </h2>
          </div>
          <SplitEditor
            articleId={completedArticle.id}
            initialContent={completedArticle.content}
          />
        </div>
      )}
    </>
  );
}

export default function WriterPage() {
  return (
    <MainLayout>
      <div className="max-w-[1400px] mx-auto">
        <Suspense fallback={
          <div className="flex items-center justify-center h-[60vh]">
            <Loader2 className="animate-spin text-primary" size={48} />
          </div>
        }>
          <WriterContent />
        </Suspense>
      </div>
    </MainLayout>
  );
}
