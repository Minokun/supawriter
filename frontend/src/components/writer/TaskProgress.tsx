'use client';

import { useEffect, useState, useRef } from 'react';
import { streamArticleProgress, type ArticleProgressEvent } from '@/lib/articles';
import { Loader2, Search, FileText, Image as ImageIcon, CheckCircle, XCircle, ExternalLink, BookOpen } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface TaskProgressProps {
  taskId: string;
  onComplete?: (data: any) => void;
}

export function TaskProgress({ taskId, onComplete }: TaskProgressProps) {
  const [progress, setProgress] = useState(0);
  const [step, setStep] = useState('正在初始化任务...');
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [searchStats, setSearchStats] = useState<any>(null);
  const [outline, setOutline] = useState<any>(null);
  const [images, setImages] = useState<any[]>([]);
  const [references, setReferences] = useState<any[]>([]);
  const [liveArticle, setLiveArticle] = useState('');
  const [isCompleted, setIsCompleted] = useState(false);
  const [isFailed, setIsFailed] = useState(false);
  const [chapterIndex, setChapterIndex] = useState<number | null>(null);
  const [chapterTotal, setChapterTotal] = useState<number | null>(null);
  const cleanupRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    cleanupRef.current = streamArticleProgress(
      taskId,
      (event: ArticleProgressEvent) => {
        // Update basic progress info
        setProgress(event.progress_percent);
        if (event.current_step) {
            setStep(event.current_step);
        }

        // Extract chapter info only during writing phase
        // Clear chapter info when not in writing phase to prevent stale data display
        const chapterMatch = event.current_step?.match(/\((\d+)\/(\d+)\)/);
        if (event.type === 'writing' && chapterMatch) {
          setChapterIndex(parseInt(chapterMatch[1]));
          setChapterTotal(parseInt(chapterMatch[2]));
        } else if (event.type !== 'writing') {
          // Clear chapter info when not in writing phase (e.g., searching, scraping, inserting images)
          setChapterIndex(null);
          setChapterTotal(null);
        }

        if (event.data) {
          if (event.data.search_results) {
            setSearchResults(event.data.search_results);
          }
          if (event.data.search_stats) {
            setSearchStats(event.data.search_stats);
          }
          if (event.data.outline) {
            setOutline(event.data.outline);
          }
          if (event.data.images) {
            setImages(event.data.images);
          }
          if (event.data.references) {
            setReferences(event.data.references);
          }
          if (event.data.live_article) {
            setLiveArticle(event.data.live_article);
          }
          if (event.data.article) {
            setIsCompleted(true);
            setStep('文章生成完成！');
            onComplete?.(event.data.article);
          }
        }

        if (event.type === 'error' || event.status === 'failed' || event.type === 'failed') {
          setIsFailed(true);
          setIsCompleted(true);
          setStep(event.data?.error_message || event.current_step || '生成任务出现错误');
        }
        
        if (event.status === 'completed' && !isCompleted) {
            setIsCompleted(true);
            setStep('文章生成完成！');
        }
      },
      (error) => {
        console.error('Stream error:', error);
        setIsFailed(true);
        setIsCompleted(true);
        setStep('连接中断或任务已失效');
      }
    );

    return () => {
      cleanupRef.current?.();
    };
  }, [taskId, onComplete]);

  return (
    <div className="space-y-6" data-testid="task-progress">
      {/* Main Progress Card */}
      <div className="bg-white rounded-lg shadow-sm border border-border p-6">
        {/* Header with icon */}
        <div className="flex items-center gap-3 mb-4">
          {isFailed ? (
            <XCircle className="w-6 h-6 text-red-500" />
          ) : isCompleted ? (
            <CheckCircle className="w-6 h-6 text-green-500" />
          ) : (
            <Loader2 className="w-6 h-6 text-primary animate-spin" />
          )}
          <div className="flex-1">
            <h3 className={`font-semibold ${isFailed ? 'text-red-700' : 'text-text-primary'}`}>
              {isFailed ? '文章生成失败' : isCompleted ? '文章生成完成' : '正在生成文章...'}
            </h3>
            <p className={`text-sm mt-1 ${isFailed ? 'text-red-500' : 'text-text-secondary'}`} data-testid="current-step">{step}</p>
          </div>
          {!isFailed && (
            <span className="text-2xl font-bold text-primary" data-testid="progress-percent">
              {isCompleted ? 100 : progress}%
            </span>
          )}
        </div>

        {/* Progress Bar */}
        <div className="space-y-2">
          <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
            <div
              className={`h-3 rounded-full transition-all duration-500 ease-out ${
                isFailed ? 'bg-red-500' : 'bg-gradient-to-r from-primary to-green-500'
              }`}
              style={{ width: isFailed ? '100%' : `${isCompleted ? 100 : progress}%` }}
            />
          </div>
          {chapterIndex && chapterTotal && !isCompleted && (
            <p className="text-xs text-text-secondary text-center">
              正在撰写第 {chapterIndex} 章节，共 {chapterTotal} 章
            </p>
          )}
        </div>
      </div>

      {/* Progress Steps Timeline */}
      <div className="bg-white rounded-lg shadow-sm border border-border p-6">
        <h4 className="font-semibold text-text-primary mb-4">生成步骤</h4>
        <div className="space-y-3">
          <StepItem
            icon={<Search className="w-4 h-4" />}
            label="搜索相关内容"
            completed={isCompleted || progress >= 30}
            active={!isCompleted && progress < 30}
            itemCount={searchResults.length}
          />
          <StepItem
            icon={<FileText className="w-4 h-4" />}
            label="生成文章大纲"
            completed={isCompleted || progress >= 60}
            active={!isCompleted && progress >= 30 && progress < 60}
            itemCount={outline ? 1 : 0}
          />
          <StepItem
            icon={<ImageIcon className="w-4 h-4" />}
            label="插入图片"
            completed={isCompleted || progress >= 95}
            active={!isCompleted && progress >= 60 && progress < 95}
            itemCount={images.length}
          />
          <StepItem
            icon={<CheckCircle className="w-4 h-4" />}
            label="完成"
            completed={isCompleted}
            active={false}
          />
        </div>
      </div>

      {/* Search Statistics Card */}
      {searchStats && (
        <div className="bg-white rounded-lg shadow-sm border border-border p-6">
          <h4 className="font-semibold text-text-primary mb-4 flex items-center gap-2">
            <Search className="w-4 h-4 text-primary" />
            搜索统计
          </h4>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            <div className="space-y-1">
              <p className="text-[10px] text-text-tertiary uppercase font-bold tracking-wider">原始查询</p>
              <p className="text-sm text-text-primary font-medium truncate" title={searchStats.original_query}>
                {searchStats.original_query}
              </p>
            </div>
            <div className="space-y-1">
              <p className="text-[10px] text-text-tertiary uppercase font-bold tracking-wider">优化查询</p>
              <p className="text-sm text-text-primary font-medium truncate" title={searchStats.optimized_query}>
                {searchStats.optimized_query}
              </p>
            </div>
            <div className="space-y-1">
              <p className="text-[10px] text-text-tertiary uppercase font-bold tracking-wider">初始搜索结果</p>
              <p className="text-sm text-text-secondary">{searchStats.total_before_llm_filter}</p>
            </div>
            <div className="space-y-1">
              <p className="text-[10px] text-text-tertiary uppercase font-bold tracking-wider">LLM过滤</p>
              <p className="text-sm text-text-secondary">{searchStats.total_after_llm_filter}</p>
            </div>
            <div className="space-y-1">
              <p className="text-[10px] text-text-tertiary uppercase font-bold tracking-wider">去重后</p>
              <p className="text-sm text-text-secondary">{searchStats.total_after_dedup}</p>
            </div>
            <div className="space-y-1">
              <p className="text-[10px] text-text-tertiary uppercase font-bold tracking-wider">最终结果</p>
              <p className="text-sm text-green-600 font-bold">{searchStats.final_count}</p>
            </div>
            <div className="space-y-1">
              <p className="text-[10px] text-text-tertiary uppercase font-bold tracking-wider">最终来源分布</p>
              <p className="text-sm text-text-primary">
                DDGS: <span className="font-bold text-primary">{searchStats.ddgs_count}</span>
                <span className="mx-1">/</span>
                Serper: <span className="font-bold text-primary">{searchStats.serper_count}</span>
              </p>
            </div>
            <div className="space-y-1 col-span-2">
              <p className="text-[10px] text-text-tertiary uppercase font-bold tracking-wider">图片来源</p>
              <p className="text-sm text-text-primary">
                网页: <span className="font-bold text-primary">{searchStats.web_images_count}</span>
                {searchStats.total_images_count > searchStats.web_images_count && (
                  <span className="ml-2">
                    DDGS: <span className="font-bold text-primary">{searchStats.total_images_count - searchStats.web_images_count}</span>
                  </span>
                )}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Collapsible Panels */}
      {searchResults.length > 0 && (
        <details className="group bg-white rounded-lg shadow-sm border border-border overflow-hidden" open data-testid="search-results">
          <summary className="cursor-pointer p-4 flex items-center justify-between hover:bg-gray-50 transition-colors">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 bg-primary/10 rounded-lg flex items-center justify-center">
                <Search className="w-4 h-4 text-primary" />
              </div>
              <span className="font-semibold text-text-primary">搜索来源</span>
              <span className="text-xs bg-primary text-white px-2 py-0.5 rounded-full font-bold">
                {searchResults.length}
              </span>
            </div>
            <span className="text-xs text-text-secondary group-open:rotate-180 transition-transform">▼</span>
          </summary>
          <div className="p-4 pt-2 max-h-[400px] overflow-y-auto space-y-3">
            {searchResults.map((result, i) => (
              <div key={i} className="p-4 bg-bg-secondary hover:bg-bg rounded-xl border border-transparent hover:border-primary/10 transition-all group/item">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <h5 className="font-bold text-sm text-text-primary group-hover/item:text-primary transition-colors line-clamp-1 flex-1">
                        {result.title}
                      </h5>
                      {result.source && (
                        <span className="text-[9px] bg-primary/10 text-primary px-1.5 py-0.5 rounded uppercase font-bold tracking-wider">
                          {result.source === 'serper' ? 'Serper' : 'DDGS'}
                        </span>
                      )}
                    </div>
                    {result.snippet && (
                      <p className="text-xs text-text-secondary mt-1.5 leading-relaxed line-clamp-2 italic">
                        &ldquo;{result.snippet}&rdquo;
                      </p>
                    )}
                    <div className="flex items-center gap-2 mt-2">
                      <span className="text-[10px] bg-white border border-border px-1.5 py-0.5 rounded text-text-tertiary font-mono truncate max-w-[250px]">
                        {result.url}
                      </span>
                    </div>
                  </div>
                  <a 
                    href={result.url} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="p-2 bg-white rounded-lg shadow-sm text-text-tertiary hover:text-primary hover:shadow-md transition-all"
                    title="查看原文"
                  >
                    <ExternalLink size={14} />
                  </a>
                </div>
              </div>
            ))}
          </div>
        </details>
      )}

      {outline && (
        <details className="group bg-white rounded-lg shadow-sm border border-border overflow-hidden" data-testid="outline-preview">
          <summary className="cursor-pointer p-4 flex items-center justify-between hover:bg-gray-50">
            <div className="flex items-center gap-2">
              <FileText className="w-4 h-4 text-primary" />
              <span className="font-medium text-text-primary">大纲预览</span>
            </div>
            <span className="text-xs text-text-secondary group-open:rotate-180 transition-transform">▼</span>
          </summary>
          <div className="p-4 pt-0">
            <div className="p-4 bg-bg-secondary rounded-lg">
              <h5 className="font-semibold text-text-primary">{outline.title}</h5>
              {outline.summary && (
                <p className="text-sm text-text-secondary mt-2">{outline.summary}</p>
              )}
              <div className="mt-4 space-y-2">
                {outline.content_outline?.map((section: any, i: number) => (
                  <div key={i} className="text-sm">
                    <p className="font-medium text-text-primary">{section.h1}</p>
                    {section.h2 && (
                      <ul className="ml-4 mt-1 text-text-secondary space-y-1">
                        {section.h2.map((sub: string, j: number) => (
                          <li key={j} className="text-xs">• {sub}</li>
                        ))}
                      </ul>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </details>
      )}

      {references.length > 0 && (
        <details className="group bg-white rounded-lg shadow-sm border border-border overflow-hidden">
          <summary className="cursor-pointer p-4 flex items-center justify-between hover:bg-gray-50 transition-colors">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 bg-green-50 rounded-lg flex items-center justify-center">
                <BookOpen className="w-4 h-4 text-green-600" />
              </div>
              <span className="font-semibold text-text-primary">参考来源</span>
              <span className="text-xs bg-green-600 text-white px-2 py-0.5 rounded-full font-bold">
                {references.length}
              </span>
            </div>
            <span className="text-xs text-text-secondary group-open:rotate-180 transition-transform">▼</span>
          </summary>
          <div className="p-4 pt-2 max-h-[300px] overflow-y-auto space-y-2">
            {references.map((ref: any, i: number) => (
              <div key={i} className="flex items-center gap-2 p-2 bg-bg-secondary rounded-lg hover:bg-bg transition-colors">
                <span className="text-xs text-text-tertiary w-6 text-center flex-shrink-0">{i + 1}</span>
                <a
                  href={ref.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-primary hover:underline truncate flex-1"
                  title={ref.url}
                >
                  {ref.title || ref.url}
                </a>
                <ExternalLink size={12} className="text-text-tertiary flex-shrink-0" />
              </div>
            ))}
          </div>
        </details>
      )}

      {images.length > 0 && (
        <details className="group bg-white rounded-lg shadow-sm border border-border overflow-hidden" data-testid="images-preview">
          <summary className="cursor-pointer p-4 flex items-center justify-between hover:bg-gray-50">
            <div className="flex items-center gap-2">
              <ImageIcon className="w-4 h-4 text-primary" />
              <span className="font-medium text-text-primary">图片资源</span>
              <span className="text-xs bg-primary text-white px-2 py-0.5 rounded-full">
                {images.length}
              </span>
            </div>
            <span className="text-xs text-text-secondary group-open:rotate-180 transition-transform">▼</span>
          </summary>
          <div className="p-4 pt-0">
            <div className="grid grid-cols-3 gap-3 max-h-60 overflow-y-auto">
              {images.map((img, i) => (
                <div key={i} className="relative aspect-video bg-bg-secondary rounded-lg overflow-hidden">
                  <img
                    src={img.url || img}
                    alt={`Image ${i + 1}`}
                    className="w-full h-full object-cover"
                  />
                </div>
              ))}
            </div>
          </div>
        </details>
      )}

      {/* Live Preview */}
      {liveArticle && (
        <div className="bg-white rounded-lg shadow-sm border border-border p-6" data-testid="live-preview">
          <div className="flex items-center gap-2 mb-4">
            <FileText className="w-4 h-4 text-primary" />
            <h4 className="font-semibold text-text-primary">实时文章预览</h4>
            {chapterIndex && chapterTotal && !isCompleted && (
              <span className="text-xs bg-primary/10 text-primary px-2 py-0.5 rounded-full">
                {chapterIndex}/{chapterTotal}
              </span>
            )}
          </div>
          <div className="bg-bg-secondary rounded-lg p-4 max-h-[600px] overflow-y-auto prose prose-lg max-w-full text-text-primary">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{liveArticle}</ReactMarkdown>
          </div>
        </div>
      )}

      {isFailed && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-center" data-testid="generation-failed">
          <XCircle className="w-8 h-8 text-red-500 mx-auto mb-2" />
          <p className="text-red-700 font-semibold">文章生成异常</p>
          <p className="text-sm text-red-600 mt-1">{step}</p>
          <p className="text-xs text-red-400 mt-2">请返回重试，或清空队列后重新提交</p>
        </div>
      )}

      {isCompleted && !isFailed && progress === 100 && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4 text-center" data-testid="generation-complete">
          <CheckCircle className="w-8 h-8 text-green-500 mx-auto mb-2" />
          <p className="text-green-700 font-semibold">文章生成完成！</p>
          <p className="text-sm text-green-600 mt-1">您可以查看、编辑或下载文章</p>
        </div>
      )}
    </div>
  );
}

// Step Item Component
interface StepItemProps {
  icon: React.ReactNode;
  label: string;
  completed: boolean;
  active: boolean;
  itemCount?: number;
}

function StepItem({ icon, label, completed, active, itemCount }: StepItemProps) {
  return (
    <div className={`flex items-center gap-3 p-2 rounded-lg transition-colors ${
      completed ? 'bg-green-50' : active ? 'bg-primary/10' : 'bg-gray-50'
    }`}>
      <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
        completed ? 'bg-green-500 text-white' : active ? 'bg-primary text-white' : 'bg-gray-300 text-gray-600'
      }`}>
        {completed ? <CheckCircle className="w-4 h-4" /> : icon}
      </div>
      <div className="flex-1">
        <p className={`text-sm font-medium ${
          completed ? 'text-green-700' : active ? 'text-primary' : 'text-text-secondary'
        }`}>
          {label}
        </p>
      </div>
      {itemCount !== undefined && itemCount > 0 && (
        <span className={`text-xs px-2 py-1 rounded-full ${
          completed ? 'bg-green-100 text-green-700' : active ? 'bg-primary/20 text-primary' : 'bg-gray-200 text-gray-600'
        }`}>
          {itemCount}
        </span>
      )}
    </div>
  );
}
