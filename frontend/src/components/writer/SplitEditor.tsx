'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import React from 'react';
import dynamic from 'next/dynamic';
import { Button } from '@/components/ui/Button';
import { Loader2, Download, Save, Palette, FileText, Code, Check } from 'lucide-react';
import { historyApi } from '@/types/api';
import type { PlatformType, PlatformConvertResponse } from '@/types/api';
import { useAuth } from '@/hooks/useAuth';
import { injectMarkdownWatermarkIfNeeded } from '@/lib/watermark';
import { sanitizePreviewHtml } from '@/lib/sanitize-preview-html';
import { ScoreCard } from './ScoreCard';

// Debounce hook
function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(timer);
    };
  }, [value, delay]);

  return debouncedValue;
}

// 预览风格配置（可扩展）
export const PREVIEW_STYLES = {
  wechat: {
    label: '公众号风格',
    description: '适合微信公众号发布',
    apiStyle: 'wechat',
  },
  zhihu: {
    label: '知乎风格',
    description: '专业且简洁的问答风格',
    apiStyle: 'zhihu',
  },
  modern: {
    label: '现代风格',
    description: '简洁现代的阅读体验',
    apiStyle: 'modern',
  },
  futuristic: {
    label: '未来风格',
    description: '科技感十足的暗色展示',
    apiStyle: 'futuristic',
  },
  elegant: {
    label: '雅致风格',
    description: '优美的排版与色调',
    apiStyle: 'elegant',
  },
  github: {
    label: 'GitHub 风格',
    description: '开发者熟悉的样式',
    apiStyle: 'github',
  },
} as const;

export type PreviewStyle = keyof typeof PREVIEW_STYLES;

const PLATFORM_OPTIONS: { key: PlatformType; label: string }[] = [
  { key: 'wechat', label: '微信公众号' },
  { key: 'zhihu', label: '知乎' },
  { key: 'xiaohongshu', label: '小红书' },
  { key: 'toutiao', label: '头条号' },
];

// 动态导入重型组件，显式处理命名导出
const Editor = dynamic(
  () => import('@monaco-editor/react').then(mod => ({ default: mod.Editor })),
  {
    ssr: false,
    loading: () => <div className="h-[600px] w-full bg-bg animate-pulse flex items-center justify-center text-text-tertiary">正在初始化源码编辑器...</div>
  }
);

const EnhancedMarkdown = dynamic(() => import('./EnhancedMarkdown').then(mod => mod.default), {
  ssr: false,
  loading: () => <div className="h-[600px] w-full bg-bg animate-pulse flex items-center justify-center text-text-tertiary">正在准备预览引擎...</div>
});

interface SplitEditorProps {
  articleId?: string;
  initialContent?: string;
  onSave?: (content: string) => void | Promise<void>;
}

/**
 * Style Selector Component
 */
const StyleSelector = ({
  currentStyle,
  onChange,
}: {
  currentStyle: PreviewStyle;
  onChange: (style: PreviewStyle) => void;
}) => {
  return (
    <div className="flex items-center gap-2">
      <Palette size={16} className="text-text-secondary" />
      <select
        value={currentStyle}
        onChange={(e) => onChange(e.target.value as PreviewStyle)}
        className="px-2 py-1 text-sm border border-border rounded bg-bg-secondary text-text-primary focus:ring-1 focus:ring-primary outline-none transition-all"
      >
        {Object.entries(PREVIEW_STYLES).map(([key, config]) => (
          <option key={key} value={key}>
            {config.label}
          </option>
        ))}
      </select>
    </div>
  );
};

// 平台缓存工具
const PLATFORM_CACHE_PREFIX = 'platform_cache_';
const PLATFORM_CACHE_EXPIRY = 60 * 60 * 1000; // 1小时过期

interface CachedPlatform {
  data: PlatformConvertResponse;
  timestamp: number;
  platform: PlatformType;
}

const getCachedPlatform = (content: string, platform: PlatformType): PlatformConvertResponse | null => {
  try {
    const key = PLATFORM_CACHE_PREFIX + platform + '_' + content.slice(0, 100);
    const cached = localStorage.getItem(key);
    if (!cached) return null;
    const parsed: CachedPlatform = JSON.parse(cached);
    // 检查是否过期
    if (Date.now() - parsed.timestamp > PLATFORM_CACHE_EXPIRY) {
      localStorage.removeItem(key);
      return null;
    }
    // 检查内容是否匹配
    if (parsed.platform !== platform) {
      return null;
    }
    return parsed.data;
  } catch {
    return null;
  }
};

const setCachedPlatform = (content: string, platform: PlatformType, data: PlatformConvertResponse) => {
  try {
    const key = PLATFORM_CACHE_PREFIX + platform + '_' + content.slice(0, 100);
    const cache: CachedPlatform = {
      data,
      timestamp: Date.now(),
      platform
    };
    localStorage.setItem(key, JSON.stringify(cache));
  } catch (e) {
    console.warn('Failed to cache platform:', e);
  }
};

const PlatformSelector = ({
  platform,
  onChange,
}: {
  platform: PlatformType;
  onChange: (platform: PlatformType) => void;
}) => {
  return (
    <div className="flex items-center gap-2">
      <select
        value={platform}
        onChange={(e) => onChange(e.target.value as PlatformType)}
        className="px-3 py-1.5 rounded-lg text-sm border border-border bg-bg-secondary text-text-primary hover:bg-bg-tertiary transition-colors focus:ring-1 focus:ring-primary outline-none cursor-pointer"
      >
        {PLATFORM_OPTIONS.map((item) => (
          <option key={item.key} value={item.key}>
            {item.label}
          </option>
        ))}
      </select>
    </div>
  );
};

export function SplitEditor({ articleId, initialContent = '', onSave }: SplitEditorProps) {
  const { userInfo } = useAuth();
  const [content, setContent] = useState(initialContent);
  const [mode, setMode] = useState<'preview' | 'edit'>('preview');
  const [previewPlatform, setPreviewPlatform] = useState<PlatformType>('wechat');
  const [previewStyle, setPreviewStyle] = useState<PreviewStyle>('wechat');
  const [platformPreview, setPlatformPreview] = useState<PlatformConvertResponse | null>(null);
  const [platformPreviewLoading, setPlatformPreviewLoading] = useState(false);
  const [platformPreviewError, setPlatformPreviewError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [editorLoading, setEditorLoading] = useState(true);
  const [editorError, setEditorError] = useState<string | null>(null);

  // 复制状态
  const [copyingMd, setCopyingMd] = useState(false);
  const [copiedMd, setCopiedMd] = useState(false);
  const [copyingHtml, setCopyingHtml] = useState(false);
  const [copiedHtml, setCopiedHtml] = useState(false);

  // Refs for synchronized scrolling
  const editorRef = useRef<any>(null);
  const previewContainerRef = useRef<HTMLDivElement>(null);
  const isScrollingRef = useRef<{ editor: boolean; preview: boolean }>({
    editor: false,
    preview: false,
  });
  const scrollTimeoutRef = useRef<any>(null);

  useEffect(() => {
    setContent(initialContent);
  }, [initialContent]);

  const outputContent = userInfo?.membership_tier
    ? injectMarkdownWatermarkIfNeeded(content, userInfo.membership_tier)
    : content;

  // 使用 debounced content，避免频繁请求
  const debouncedContent = useDebounce(content, 800); // 800ms 防抖

  // Fetch platform preview when in preview mode (with caching)
  useEffect(() => {
    if (mode !== 'preview') {
      return;
    }

    // 如果内容为空或太短，不请求
    if (!debouncedContent || debouncedContent.length < 10) {
      return;
    }

    let cancelled = false;

    const fetchPlatformPreview = async () => {
      // 先尝试从缓存加载
      const cached = getCachedPlatform(debouncedContent, previewPlatform);
      if (cached && !cancelled) {
        setPlatformPreview(cached);
        setPlatformPreviewLoading(false);
        return;
      }

      setPlatformPreviewLoading(true);
      setPlatformPreviewError(null);
      try {
        const result = await historyApi.convertPlatform(debouncedContent, previewPlatform);
        if (!cancelled) {
          setPlatformPreview(result);
          // 缓存结果
          setCachedPlatform(debouncedContent, previewPlatform, result);
        }
      } catch (error) {
        if (!cancelled) {
          setPlatformPreviewError('平台转换失败，请重试');
        }
      } finally {
        if (!cancelled) {
          setPlatformPreviewLoading(false);
        }
      }
    };

    fetchPlatformPreview();
    return () => {
      cancelled = true;
    };
  }, [debouncedContent, previewPlatform, mode]);

  // Synchronized scrolling handler
  const handleEditorScroll = () => {
    if (isScrollingRef.current.preview) return;
    isScrollingRef.current.editor = true;

    if (!editorRef.current || !previewContainerRef.current) return;

    const editor = editorRef.current;
    const scrollHeight = editor.getScrollHeight() - editor.getLayoutInfo().height;
    const scrollTop = editor.getScrollTop();

    if (scrollHeight <= 0) {
        isScrollingRef.current.editor = false;
        return;
    }

    const scrollRatio = scrollTop / scrollHeight;

    const preview = previewContainerRef.current;
    const previewScrollHeight = preview.scrollHeight - preview.clientHeight;
    preview.scrollTop = scrollRatio * previewScrollHeight;

    if (scrollTimeoutRef.current) clearTimeout(scrollTimeoutRef.current);
    scrollTimeoutRef.current = setTimeout(() => {
      isScrollingRef.current.editor = false;
    }, 150);
  };

  const handlePreviewScroll = () => {
    if (isScrollingRef.current.editor) return;
    isScrollingRef.current.preview = true;

    const preview = previewContainerRef.current;
    if (!preview || !editorRef.current) {
        isScrollingRef.current.preview = false;
        return;
    }

    const previewScrollTop = preview.scrollTop;
    const previewScrollHeight = preview.scrollHeight - preview.clientHeight;

    if (previewScrollHeight <= 0) {
        isScrollingRef.current.preview = false;
        return;
    }

    const scrollRatio = previewScrollTop / previewScrollHeight;

    const editor = editorRef.current;
    const editorScrollHeight = editor.getScrollHeight() - editor.getLayoutInfo().height;
    editor.setScrollTop(scrollRatio * editorScrollHeight);

    if (scrollTimeoutRef.current) clearTimeout(scrollTimeoutRef.current);
    scrollTimeoutRef.current = setTimeout(() => {
      isScrollingRef.current.preview = false;
    }, 150);
  };

  const handleSave = async () => {
    setIsSaving(true);
    setSaveSuccess(false);

    try {
      if (onSave) {
        await onSave(content);
      } else if (articleId) {
        await historyApi.updateArticle(articleId, content);
      } else {
        return;
      }

      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 2000);
    } catch (error) {
      console.error('Save failed:', error);
      alert('保存失败，请重试');
    } finally {
      setIsSaving(false);
    }
  };

  const handleDownload = () => {
    const blob = new Blob([outputContent], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `article-${Date.now()}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // 复制 Markdown 原文
  const handleCopyMd = async () => {
    setCopyingMd(true);
    try {
      await navigator.clipboard.writeText(outputContent);
      setCopiedMd(true);
      setTimeout(() => setCopiedMd(false), 2000);
    } catch (error) {
      console.error('Copy MD failed:', error);
      alert('复制失败，请手动复制');
    } finally {
      setCopyingMd(false);
    }
  };

  // 按平台复制（HTML/Markdown/纯文本）
  const handleCopyHtml = async () => {
    setCopyingHtml(true);
    try {
      const response = await historyApi.convertPlatform(content, previewPlatform);
      if (response.copy_format === 'rich_text' && response.format === 'html') {
        await navigator.clipboard.write([
          new ClipboardItem({
            'text/html': new Blob([response.content], { type: 'text/html' }),
            'text/plain': new Blob([outputContent], { type: 'text/plain' }),
          }),
        ]);
      } else {
        await navigator.clipboard.writeText(response.content);
      }

      setCopiedHtml(true);
      setTimeout(() => setCopiedHtml(false), 2000);
    } catch (error) {
      console.error('Copy HTML failed:', error);
      alert('复制失败，请重试');
    } finally {
      setCopyingHtml(false);
    }
  };

  return (
    <div className="space-y-4" data-testid="split-editor">
      {/* Toolbar: Mode Toggle, Style Selector, Action Buttons */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <button
            onClick={() => setMode('preview')}
            className={`px-4 py-2 rounded-lg transition-colors ${
              mode === 'preview'
                ? 'bg-primary text-white'
                : 'bg-bg-secondary text-text-primary hover:bg-bg-tertiary'
            }`}
            data-testid="mode-preview"
          >
            预览模式
          </button>
          <button
            onClick={() => setMode('edit')}
            className={`px-4 py-2 rounded-lg transition-colors ${
              mode === 'edit'
                ? 'bg-primary text-white'
                : 'bg-bg-secondary text-text-primary hover:bg-bg-tertiary'
            }`}
            data-testid="mode-edit"
          >
            编辑模式
          </button>

          {/* 分隔线 */}
          <div className="w-px h-6 bg-border mx-1" />

          {mode === 'preview' ? (
            <PlatformSelector platform={previewPlatform} onChange={setPreviewPlatform} />
          ) : (
            <StyleSelector currentStyle={previewStyle} onChange={setPreviewStyle} />
          )}
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-2">
          <Button
            variant="primary"
            size="sm"
            icon={isSaving ? <Loader2 className="animate-spin" size={16} /> : <Save size={16} />}
            onClick={handleSave}
            disabled={isSaving}
          >
            {isSaving ? '保存中...' : saveSuccess ? '✓ 已保存' : '保存'}
          </Button>
          <Button
            variant="secondary"
            size="sm"
            icon={<Download size={16} />}
            onClick={handleDownload}
          >
            下载
          </Button>

          {/* 分隔线 */}
          <div className="w-px h-6 bg-border mx-1" />

          {/* Markdown 复制按钮 */}
          <Button
            variant="secondary"
            size="sm"
            icon={
              copyingMd ? (
                <Loader2 className="animate-spin" size={16} />
              ) : copiedMd ? (
                <Check size={16} className="text-green-500" />
              ) : (
                <FileText size={16} />
              )
            }
            onClick={handleCopyMd}
            disabled={copyingMd}
          >
            {copiedMd ? '已复制' : '复制 MD'}
          </Button>

          {/* HTML 格式复制按钮 */}
          <Button
            variant="secondary"
            size="sm"
            icon={
              copyingHtml ? (
                <Loader2 className="animate-spin" size={16} />
              ) : copiedHtml ? (
                <Check size={16} className="text-green-500" />
              ) : (
                <Code size={16} />
              )
            }
            onClick={handleCopyHtml}
            disabled={copyingHtml}
          >
            {copiedHtml ? '已复制' : '一键复制'}
          </Button>
        </div>
      </div>

      {/* 评分卡片（F4） */}
      <ScoreCard articleId={articleId} />

      {/* Preview Mode */}
      {mode === 'preview' && (
        <div className="border border-border rounded-lg overflow-hidden bg-white" data-testid="preview-container">
          <div className="p-4 bg-bg-secondary border-b border-border flex items-center justify-between">
            <span className="text-sm text-text-secondary">
              📱 {PLATFORM_OPTIONS.find((item) => item.key === previewPlatform)?.label || '平台'} 预览
            </span>
          </div>
          <div className="max-h-[700px] overflow-y-auto">
            {platformPreviewLoading ? (
              <div className="p-8 text-center text-text-secondary">正在转换平台格式...</div>
            ) : platformPreviewError ? (
              <div className="p-8 text-center text-error">{platformPreviewError}</div>
            ) : platformPreview?.format === 'html' ? (
              <div
                className="p-4"
                dangerouslySetInnerHTML={{ __html: sanitizePreviewHtml(platformPreview.content) }}
              />
            ) : platformPreview?.format === 'markdown' ? (
              <EnhancedMarkdown
                content={platformPreview.content}
                style={previewPlatform === 'zhihu' ? 'zhihu' : 'wechat'}
                readOnly={true}
              />
            ) : (
              <pre className="p-6 whitespace-pre-wrap text-text-primary leading-7">
                {platformPreview?.content || ''}
              </pre>
            )}
          </div>
        </div>
      )}

      {/* Edit Mode with Split View */}
      {mode === 'edit' && (
        <div className="grid grid-cols-2 gap-4 animate-in fade-in duration-300">
          {/* Monaco Editor */}
          <div className="border border-border rounded-lg overflow-hidden flex flex-col bg-white relative">
            <div className="p-2 bg-bg-secondary border-b border-border text-sm text-text-secondary flex items-center justify-between">
              <span>✏️ Markdown 源码</span>
            </div>
            <div className="flex-1 relative min-h-[600px]">
              <Editor
                height="600px"
                defaultLanguage="markdown"
                value={content}
                onChange={(value) => setContent(value || '')}
                onMount={(editor) => {
                  editorRef.current = editor;
                  setEditorLoading(false);

                  // 使用 Monaco 原生滚动事件监听实现同步滚动
                  editor.onDidScrollChange(() => {
                    handleEditorScroll();
                  });
                }}
                onValidate={(errors) => {
                  if (errors.length > 0) {
                    console.error('Monaco Editor validation errors:', errors);
                  }
                }}
                theme="vs-light"
                loading={<div className="h-[600px] w-full flex items-center justify-center text-text-tertiary">加载编辑器中...</div>}
                options={{
                  minimap: { enabled: false },
                  fontSize: 14,
                  lineNumbers: 'on',
                  scrollBeyondLastLine: false,
                  wordWrap: 'on',
                  padding: { top: 20 },
                }}
              />
              {editorError && (
                <div className="absolute inset-0 flex items-center justify-center bg-red-50">
                  <div className="text-center">
                    <p className="text-red-600 mb-2">编辑器加载失败</p>
                    <p className="text-sm text-red-500">{editorError}</p>
                    <button
                      onClick={() => {
                        setEditorError(null);
                        setEditorLoading(true);
                      }}
                      className="mt-2 px-4 py-2 bg-red-600 text-white rounded"
                    >
                      重试
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Novel Preview */}
          <div className="border border-border rounded-lg overflow-hidden flex flex-col bg-white">
            <div className="p-2 bg-bg-secondary border-b border-border text-sm text-text-secondary">
              <span>👁️ 实时渲染预览</span>
            </div>
            <div
              ref={previewContainerRef}
              className="flex-1 overflow-y-auto max-h-[600px]"
              onScroll={handlePreviewScroll}
            >
              <EnhancedMarkdown
                key={`edit-preview-${previewStyle}-${content}`}
                content={content}
                style={previewStyle}
                readOnly={true}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
