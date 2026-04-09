'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { getArticleQueue, clearArticleQueue, removeFromQueue, type ArticleTaskProgress } from '@/lib/articles';
import { Loader2, Clock, CheckCircle, XCircle, Trash2, AlertTriangle } from 'lucide-react';

interface TaskQueueProps {
  onTaskSelect?: (taskId: string) => void;
  refreshTrigger?: number;
}

export function TaskQueue({ onTaskSelect, refreshTrigger }: TaskQueueProps) {
  const [tasks, setTasks] = useState<ArticleTaskProgress[]>([]);
  const [loading, setLoading] = useState(true);
  const [clearing, setClearing] = useState(false);
  const [retrying, setRetrying] = useState(false);
  const [loadFailed, setLoadFailed] = useState(false);
  const [loadErrorMessage, setLoadErrorMessage] = useState<string | null>(null);
  const [actionErrorMessage, setActionErrorMessage] = useState<string | null>(null);
  const tasksRef = useRef<ArticleTaskProgress[]>([]);

  useEffect(() => {
    tasksRef.current = tasks;
  }, [tasks]);

  const loadQueue = async ({ manual = false }: { manual?: boolean } = {}) => {
    if (manual) {
      setRetrying(true);
    }

    try {
      const response = await getArticleQueue();
      setTasks(response.items);
      setLoadFailed(false);
      setLoadErrorMessage(null);
    } catch (error) {
      console.error('Failed to load queue:', error);
      setLoadFailed(true);
      setLoadErrorMessage(
        tasksRef.current.length > 0
          ? '任务队列刷新失败，当前展示的是最近一次成功加载的数据。'
          : '任务队列加载失败，请稍后重试。'
      );
    } finally {
      setLoading(false);
      if (manual) {
        setRetrying(false);
      }
    }
  };

  useEffect(() => {
    loadQueue();
    
    const interval = setInterval(() => {
        loadQueue();
    }, 3000);

    return () => clearInterval(interval);
  }, [refreshTrigger]);

  const handleClearQueue = async () => {
    if (clearing) return;
    setClearing(true);
    setActionErrorMessage(null);
    try {
      await clearArticleQueue();
      setTasks([]);
    } catch (error) {
      console.error('Failed to clear queue:', error);
      setActionErrorMessage('清空队列失败，请稍后重试。');
    } finally {
      setClearing(false);
    }
  };

  const handleRemoveTask = async (e: React.MouseEvent, taskId: string) => {
    e.stopPropagation();
    setActionErrorMessage(null);
    try {
      await removeFromQueue(taskId);
      setTasks(prev => prev.filter(t => t.task_id !== taskId));
    } catch (error) {
      console.error('Failed to remove task:', error);
      setActionErrorMessage('移除任务失败，请稍后重试。');
    }
  };

  const tasksToDisplay = useMemo(() => {
    const uniqueTasksMap = new Map<string, ArticleTaskProgress>();
    
    [...tasks].reverse().forEach(task => {
        uniqueTasksMap.set(task.task_id, task);
    });
    
    return Array.from(uniqueTasksMap.values()).reverse();
  }, [tasks]);

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'queued': return <Clock className="text-amber-500 animate-pulse" size={16} />;
      case 'running': return <Loader2 className="text-primary animate-spin" size={16} />;
      case 'completed': return <CheckCircle className="text-green-500" size={16} />;
      case 'failed':
      case 'error': return <XCircle className="text-red-500" size={16} />;
      default: return <Clock className="text-gray-500" size={16} />;
    }
  };

  const getStatusText = (task: ArticleTaskProgress) => {
    switch (task.status) {
      case 'running': return `正在生成 - ${task.progress}%`;
      case 'queued': return '等待队列中';
      case 'completed': return '生成完成';
      case 'failed':
      case 'error': return task.error_message || task.progress_text || '生成失败';
      default: return '未知状态';
    }
  };

  if (loading && tasks.length === 0) {
    return (
        <div className="flex flex-col items-center justify-center py-12 bg-white rounded-2xl border border-dashed border-border">
          <Loader2 className="animate-spin text-primary mb-2" size={32} />
          <p className="text-xs text-text-tertiary font-medium">获取队列中...</p>
        </div>
    );
  }

  if (tasksToDisplay.length === 0) {
    return (
      <div className="space-y-6 animate-in fade-in duration-500">
        <div className="flex items-center justify-between">
          <h3 className="font-heading text-lg font-semibold text-text-primary flex items-center gap-2">
            <span>🚀</span> 任务队列 (0)
          </h3>
        </div>

        <div className="flex flex-col items-center justify-center py-16 bg-white rounded-2xl border-2 border-dashed border-border/50 text-center">
          <div className="w-16 h-16 bg-bg rounded-full flex items-center justify-center mb-4">
            <span className="text-3xl">{loadFailed ? '⚠️' : '☕'}</span>
          </div>
          <h4 className="text-sm font-bold text-text-primary mb-1">
            {loadFailed ? '任务队列加载失败' : '当前没有进行中的任务'}
          </h4>
          <p className="text-xs text-text-secondary px-8">
            {loadFailed ? loadErrorMessage : '灵感随时可能降临，填左侧表单开启您的创作之旅'}
          </p>
          {loadFailed && (
            <button
              onClick={() => loadQueue({ manual: true })}
              disabled={retrying}
              className="mt-5 inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-primary text-white hover:opacity-90 transition-opacity disabled:opacity-60"
            >
              {retrying ? <Loader2 className="animate-spin" size={14} /> : <AlertTriangle size={14} />}
              重新加载队列
            </button>
          )}
          {actionErrorMessage && (
            <p className="mt-4 text-xs text-red-600">{actionErrorMessage}</p>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      <div className="flex items-center justify-between">
        <h3 className="font-heading text-lg font-semibold text-text-primary flex items-center gap-2">
          <span>🚀</span> 任务队列 ({tasksToDisplay.length})
        </h3>
        <button
          onClick={handleClearQueue}
          disabled={clearing}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-red-500 hover:text-white hover:bg-red-500 border border-red-200 hover:border-red-500 rounded-lg transition-all duration-200 disabled:opacity-50"
          title="清空所有队列任务"
        >
          {clearing ? <Loader2 className="animate-spin" size={12} /> : <Trash2 size={12} />}
          清空队列
        </button>
      </div>

      <div className="space-y-3">
        <p className="text-xs font-bold text-text-tertiary uppercase tracking-wider">任务列表</p>
        {(loadFailed || actionErrorMessage) && (
          <div className={`flex items-center justify-between gap-4 rounded-2xl border px-4 py-3 ${
            loadFailed ? 'bg-amber-50 border-amber-200 text-amber-900' : 'bg-red-50 border-red-200 text-red-700'
          }`}>
            <div className="flex items-center gap-2 text-sm">
              <AlertTriangle size={16} />
              <p>{loadFailed ? loadErrorMessage : actionErrorMessage}</p>
            </div>
            {loadFailed && (
              <button
                onClick={() => loadQueue({ manual: true })}
                disabled={retrying}
                className="inline-flex items-center gap-2 rounded-lg border border-amber-300 bg-white px-3 py-1.5 text-xs font-medium text-amber-900 hover:border-amber-400 disabled:opacity-60"
              >
                {retrying ? <Loader2 className="animate-spin" size={12} /> : null}
                重新加载队列
              </button>
            )}
          </div>
        )}
        <div className="space-y-2">
          {tasksToDisplay.map(task => {
            const isFailed = task.status === 'failed' || task.status === 'error';
            const canOpenProgress = task.status === 'queued' || task.status === 'running';
            return (
              <div
                key={task.task_id}
                className={`group p-4 rounded-xl border transition-all duration-300 ${
                  task.status === 'running' 
                    ? 'bg-primary/5 border-primary/20 shadow-sm' 
                    : isFailed
                    ? 'bg-red-50 border-red-200'
                    : task.status === 'completed' ? 'bg-gray-50 border-gray-100 opacity-80' : 'bg-white border-border'
                } ${canOpenProgress ? 'cursor-pointer hover:border-primary/30 hover:shadow-md' : 'cursor-default'}`}
                onClick={() => {
                  if (!canOpenProgress) return;
                  onTaskSelect?.(task.task_id);
                }}
                aria-disabled={!canOpenProgress}
              >
                <div className="flex items-center gap-3">
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
                    task.status === 'running' ? 'bg-primary/10' : isFailed ? 'bg-red-100' : 'bg-bg'
                  }`}>
                    {getStatusIcon(task.status)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className={`text-sm font-semibold truncate ${
                      task.status === 'running' ? 'text-text-primary' : isFailed ? 'text-red-700' : 'text-text-secondary'
                    }`}>
                      {task.topic || '未命名任务'}
                    </p>
                    <p className={`text-[10px] mt-0.5 font-medium truncate ${
                      isFailed ? 'text-red-500' : 'text-text-tertiary uppercase'
                    }`}>
                      {getStatusText(task)}
                    </p>
                  </div>
                  {task.status === 'running' && (
                    <div className="w-12 h-1 bg-gray-100 rounded-full overflow-hidden">
                      <div 
                        className="h-full bg-primary transition-all duration-500" 
                        style={{ width: `${task.progress}%` }}
                      />
                    </div>
                  )}
                  {(isFailed || task.status === 'completed') && (
                    <button
                      onClick={(e) => handleRemoveTask(e, task.task_id)}
                      className="opacity-0 group-hover:opacity-100 p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-all"
                      title="移除此任务"
                    >
                      <Trash2 size={14} />
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
