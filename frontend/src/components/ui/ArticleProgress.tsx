'use client';

import { useEffect, useState, useRef } from 'react';
import Card from './Card';
import { Loader2, Check, AlertCircle } from 'lucide-react';
import { streamArticleProgress, type ArticleProgressEvent } from '@/lib/articles';

interface ProgressStep {
  name: string;
  status: 'pending' | 'running' | 'completed' | 'error';
  message?: string;
  progress?: number;
  count?: number;
}

interface ArticleProgressProps {
  taskId: string;
  onComplete?: (result: any) => void;
  onError?: (error: string) => void;
}

export default function ArticleProgress({ taskId, onComplete, onError }: ArticleProgressProps) {
  const [steps, setSteps] = useState<ProgressStep[]>([
    { name: '网页爬取', status: 'pending' },
    { name: '内容分析', status: 'pending' },
    { name: '生成大纲', status: 'pending' },
    { name: '撰写章节', status: 'pending', progress: 0 },
    { name: '图片搜索', status: 'pending' },
    { name: '完成生成', status: 'pending' },
  ]);

  const [overallProgress, setOverallProgress] = useState(0);
  const [stepMessage, setStepMessage] = useState('正在初始化任务...');
  const cleanupRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    // 使用真实的WebSocket/SSE流式进度更新
    cleanupRef.current = streamArticleProgress(
      taskId,
      (event: ArticleProgressEvent) => {
        // 更新总体进度
        setOverallProgress(event.progress_percent);
        setStepMessage(event.current_step || '');

        // 根据进度百分比和当前步骤更新UI状态
        setSteps(prev => {
          const newSteps = [...prev];

          // 根据进度百分比判断当前步骤
          // 0-10%: 网页爬取
          // 10-30%: 内容分析（搜索）
          // 30-60%: 生成大纲
          // 60-95%: 撰写章节
          // 95-100%: 图片搜索和完成

          if (event.progress_percent >= 0 && event.progress_percent < 10) {
            newSteps[0].status = 'running';
            newSteps[0].message = event.current_step || '正在搜索相关内容...';
          } else if (event.progress_percent >= 10) {
            newSteps[0].status = 'completed';
            newSteps[0].message = `搜索完成 (${event.data?.search_results?.length || 0} 个结果)`;
            newSteps[0].count = event.data?.search_results?.length || 0;
          }

          if (event.progress_percent >= 10 && event.progress_percent < 30) {
            newSteps[1].status = 'running';
            newSteps[1].message = event.current_step || '正在分析内容...';
          } else if (event.progress_percent >= 30) {
            newSteps[1].status = 'completed';
            newSteps[1].message = '分析完成';
          }

          if (event.progress_percent >= 30 && event.progress_percent < 60) {
            newSteps[2].status = 'running';
            newSteps[2].message = event.current_step || '正在生成大纲...';
          } else if (event.progress_percent >= 60) {
            newSteps[2].status = 'completed';
            newSteps[2].message = event.data?.outline ? '大纲已生成' : '大纲生成完成';
          }

          if (event.progress_percent >= 60 && event.progress_percent < 95) {
            newSteps[3].status = 'running';
            // 提取章节进度 "正在撰写: 标题 (2/5)"
            const chapterMatch = event.current_step?.match(/\((\d+)\/(\d+)\)/);
            if (chapterMatch) {
              const current = parseInt(chapterMatch[1]);
              const total = parseInt(chapterMatch[2]);
              const chapterProgress = Math.round((current / total) * 100);
              newSteps[3].progress = chapterProgress;
              newSteps[3].message = `正在撰写 (${current}/${total})`;
            } else {
              // 使用总体进度计算章节进度
              const writingProgress = Math.round(((event.progress_percent - 60) / 35) * 100);
              newSteps[3].progress = writingProgress;
              newSteps[3].message = event.current_step || '正在撰写章节...';
            }
          } else if (event.progress_percent >= 95) {
            newSteps[3].status = 'completed';
            newSteps[3].progress = 100;
            newSteps[3].message = '撰写完成';
          }

          if (event.progress_percent >= 95 && event.progress_percent < 100) {
            newSteps[4].status = 'running';
            newSteps[4].message = `图片处理 (${event.data?.images?.length || 0} 张)`;
            newSteps[4].count = event.data?.images?.length || 0;
          } else if (event.progress_percent >= 100) {
            newSteps[4].status = 'completed';
            newSteps[4].message = `图片插入完成 (${event.data?.images?.length || 0} 张)`;
            newSteps[4].count = event.data?.images?.length || 0;
          }

          if (event.status === 'completed' || event.progress_percent >= 100) {
            newSteps[5].status = 'completed';
            newSteps[5].message = '文章生成完成';
          }

          return newSteps;
        });

        // 处理完成状态
        if (event.status === 'completed' || event.type === 'completed') {
          onComplete?.(event.data?.article || { success: true });
        }

        // 处理错误状态
        if (event.type === 'error' || event.status === 'error') {
          setSteps(prev => {
            const newSteps = [...prev];
            const runningIndex = newSteps.findIndex(s => s.status === 'running');
            if (runningIndex >= 0) {
              newSteps[runningIndex].status = 'error';
              newSteps[runningIndex].message = event.data?.error_message || '处理失败';
            }
            return newSteps;
          });
          onError?.(event.data?.error_message || '任务执行出错');
        }
      },
      (error) => {
        console.error('Progress stream error:', error);
        setSteps(prev => {
          const newSteps = [...prev];
          const runningIndex = newSteps.findIndex(s => s.status === 'running');
          if (runningIndex >= 0) {
            newSteps[runningIndex].status = 'error';
            newSteps[runningIndex].message = '连接中断';
          }
          return newSteps;
        });
        onError?.('连接中断或任务已失效');
      }
    );

    return () => {
      cleanupRef.current?.();
    };
  }, [taskId, onComplete, onError]);

  const getStepIcon = (step: ProgressStep) => {
    switch (step.status) {
      case 'running':
        return <Loader2 className="animate-spin text-primary" size={20} />;
      case 'completed':
        return <Check className="text-success" size={20} />;
      case 'error':
        return <AlertCircle className="text-error" size={20} />;
      default:
        return <div className="w-5 h-5 rounded-full border-2 border-border" />;
    }
  };

  const getStepColor = (step: ProgressStep) => {
    switch (step.status) {
      case 'running':
        return 'text-primary font-semibold';
      case 'completed':
        return 'text-success';
      case 'error':
        return 'text-error';
      default:
        return 'text-text-secondary';
    }
  };

  return (
    <Card padding="xl">
      <div className="flex items-center gap-3 mb-6">
        <Loader2 className="animate-spin text-primary" size={24} />
        <h3 className="font-heading text-xl font-semibold text-text-primary">
          文章生成中...
        </h3>
      </div>

      <div className="space-y-4">
        {steps.map((step, index) => (
          <div key={step.name} className="flex items-start gap-4">
            {/* 步骤图标 */}
            <div className="flex-shrink-0 mt-1">
              {getStepIcon(step)}
            </div>

            {/* 步骤信息 */}
            <div className="flex-1">
              <div className="flex items-center justify-between mb-1">
                <div className="flex items-center gap-2">
                  <span className={`font-body text-[15px] ${getStepColor(step)}`}>
                    {index + 1}. {step.name}
                  </span>
                  {step.count !== undefined && step.count > 0 && (
                    <span className="text-xs bg-primary/10 text-primary px-2 py-0.5 rounded-full font-bold">
                      {step.count}
                    </span>
                  )}
                </div>
                {step.message && (
                  <span className="font-body text-sm text-text-secondary">
                    {step.message}
                  </span>
                )}
              </div>

              {/* 进度条（仅章节撰写显示） */}
              {step.name === '撰写章节' && step.status === 'running' && (
                <div className="mt-2">
                  <div className="w-full h-2 bg-bg rounded-full overflow-hidden">
                    <div
                      className="h-full bg-primary transition-all duration-300"
                      style={{ width: `${step.progress || 0}%` }}
                    />
                  </div>
                </div>
              )}

              {/* 连接线 */}
              {index < steps.length - 1 && (
                <div
                  className={`w-0.5 h-6 ml-2.5 mt-2 ${
                    step.status === 'completed' ? 'bg-success' : 'bg-border'
                  }`}
                />
              )}
            </div>
          </div>
        ))}
      </div>

      {/* 总体进度 */}
      <div className="mt-6 pt-6 border-t-2 border-border">
        <div className="flex items-center justify-between mb-2">
          <span className="font-body text-sm font-medium text-text-primary">
            总体进度
          </span>
          <span className="font-body text-sm text-text-secondary">
            {overallProgress}%
          </span>
        </div>
        <div className="w-full h-3 bg-bg rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-primary to-secondary transition-all duration-500"
            style={{ width: `${overallProgress}%` }}
          />
        </div>
        <p className="mt-2 text-center text-sm text-text-secondary">
          {stepMessage}
        </p>
      </div>
    </Card>
  );
}
