'use client';

import { useState, useCallback } from 'react';
import { historyApi, type Article, type PlatformType } from '@/types/api';
import { copyRichTextToClipboard } from '@/lib/clipboard';
import { useToast } from '@/components/ui/ToastContainer';
import {
  X,
  Copy,
  ExternalLink,
  Check,
  Loader2,
  Send,
  FileText,
  Globe,
  MessageCircle,
  BookOpen,
  PenTool,
  Users,
  Newspaper,
} from 'lucide-react';

interface PlatformConfig {
  name: string;
  url: string;
  copyFormat: 'rich_text' | 'plain_text';
  formatLabel: string;
  icon: React.ReactNode;
}

const PLATFORMS: Record<PlatformType, PlatformConfig> = {
  wechat: {
    name: '微信公众号',
    url: 'https://mp.weixin.qq.com/',
    copyFormat: 'rich_text',
    formatLabel: 'HTML',
    icon: <MessageCircle size={20} />,
  },
  zhihu: {
    name: '知乎',
    url: 'https://zhuanlan.zhihu.com/write',
    copyFormat: 'plain_text',
    formatLabel: 'MD',
    icon: <BookOpen size={20} />,
  },
  xiaohongshu: {
    name: '小红书',
    url: 'https://creator.xiaohongshu.com/publish/publish',
    copyFormat: 'plain_text',
    formatLabel: '文本',
    icon: <Globe size={20} />,
  },
  csdn: {
    name: 'CSDN',
    url: 'https://mp.csdn.net/mp_blog/creation/editor',
    copyFormat: 'plain_text',
    formatLabel: 'MD',
    icon: <FileText size={20} />,
  },
  baijiahao: {
    name: '百家号',
    url: 'https://baijiahao.baidu.com/builder/rc/edit',
    copyFormat: 'rich_text',
    formatLabel: 'HTML',
    icon: <Newspaper size={20} />,
  },
  zsxq: {
    name: '知识星球',
    url: 'https://wx.zsxq.com/',
    copyFormat: 'plain_text',
    formatLabel: 'MD',
    icon: <Users size={20} />,
  },
  toutiao: {
    name: '今日头条',
    url: 'https://mp.toutiao.com/profile_v4/graphic/articles',
    copyFormat: 'rich_text',
    formatLabel: 'HTML',
    icon: <PenTool size={20} />,
  },
};

interface PublishModalProps {
  article: Article;
  open: boolean;
  onClose: () => void;
}

type CopyState = 'idle' | 'loading' | 'copied' | 'error';

export default function PublishModal({ article, open, onClose }: PublishModalProps) {
  const [selectedPlatforms, setSelectedPlatforms] = useState<Set<PlatformType>>(new Set());
  const [copyStates, setCopyStates] = useState<Record<string, CopyState>>({});
  const [titleCopied, setTitleCopied] = useState(false);
  const { showSuccess, showError } = useToast();

  const togglePlatform = useCallback((platform: PlatformType) => {
    setSelectedPlatforms(prev => {
      const next = new Set(prev);
      if (next.has(platform)) {
        next.delete(platform);
      } else {
        next.add(platform);
      }
      return next;
    });
  }, []);

  const handleCopyContent = useCallback(async (platform: PlatformType) => {
    const config = PLATFORMS[platform];
    setCopyStates(prev => ({ ...prev, [platform]: 'loading' }));

    try {
      const result = await historyApi.convertPlatform(
        article.content || '',
        platform,
        article.title || article.topic || ''
      );

      if (config.copyFormat === 'rich_text') {
        await copyRichTextToClipboard({ html: result.content });
      } else {
        await navigator.clipboard.writeText(result.content);
      }

      setCopyStates(prev => ({ ...prev, [platform]: 'copied' }));
      showSuccess(`${config.name}内容已复制`);

      setTimeout(() => {
        setCopyStates(prev => ({ ...prev, [platform]: 'idle' }));
      }, 2000);
    } catch (err) {
      console.error('Copy failed:', err);
      setCopyStates(prev => ({ ...prev, [platform]: 'error' }));
      showError('格式转换失败，请重试');
      setTimeout(() => {
        setCopyStates(prev => ({ ...prev, [platform]: 'idle' }));
      }, 2000);
    }
  }, [article, showSuccess, showError]);

  const handleCopyTitle = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(article.title || article.topic || '');
      setTitleCopied(true);
      showSuccess('标题已复制');
      setTimeout(() => setTitleCopied(false), 2000);
    } catch {
      showError('复制失败，请检查浏览器权限');
    }
  }, [article, showSuccess, showError]);

  const handleOpenPlatform = useCallback((platform: PlatformType) => {
    window.open(PLATFORMS[platform].url, '_blank');
  }, []);

  const handleOpenAll = useCallback(() => {
    selectedPlatforms.forEach(platform => {
      window.open(PLATFORMS[platform].url, '_blank');
    });
  }, [selectedPlatforms]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4 animate-in fade-in duration-300"
      onClick={onClose}
    >
      <div
        className="bg-surface rounded-3xl w-full max-w-2xl max-h-[85vh] flex flex-col shadow-2xl overflow-hidden animate-in zoom-in-95 duration-300"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-border bg-white/50">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-primary/10 rounded-xl text-primary">
              <Send size={22} />
            </div>
            <div className="min-w-0">
              <h2 className="font-heading text-lg font-bold text-text-primary line-clamp-1">
                一键发布
              </h2>
              <p className="text-sm text-text-secondary truncate">
                {article.title || article.topic}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="w-9 h-9 flex items-center justify-center rounded-lg hover:bg-bg-secondary transition-colors text-text-tertiary"
          >
            <X size={20} />
          </button>
        </div>

        {/* Platform List */}
        <div className="flex-1 overflow-y-auto p-6 space-y-2">
          {(Object.entries(PLATFORMS) as [PlatformType, PlatformConfig][]).map(
            ([key, config]) => {
              const isSelected = selectedPlatforms.has(key);
              const copyState = copyStates[key] || 'idle';

              return (
                <div
                  key={key}
                  className={`flex items-center gap-4 p-4 rounded-xl border transition-all ${
                    isSelected
                      ? 'border-primary/30 bg-primary/5'
                      : 'border-border/50 hover:border-border hover:bg-bg/50'
                  }`}
                >
                  <button
                    onClick={() => togglePlatform(key)}
                    className={`w-5 h-5 rounded border-2 flex items-center justify-center flex-shrink-0 transition-all ${
                      isSelected
                        ? 'bg-primary border-primary text-white'
                        : 'border-border'
                    }`}
                  >
                    {isSelected && <Check size={14} strokeWidth={3} />}
                  </button>

                  <div className="text-text-secondary flex-shrink-0">
                    {config.icon}
                  </div>

                  <div className="flex-1 min-w-0">
                    <span className="font-medium text-text-primary text-sm">
                      {config.name}
                    </span>
                    <span className="ml-2 text-xs text-text-tertiary bg-bg px-1.5 py-0.5 rounded">
                      {config.formatLabel}
                    </span>
                  </div>

                  <div className="flex items-center gap-2 flex-shrink-0">
                    <button
                      onClick={() => handleCopyContent(key)}
                      disabled={copyState === 'loading'}
                      className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                        copyState === 'copied'
                          ? 'bg-success/10 text-success'
                          : copyState === 'error'
                          ? 'bg-red-50 text-red-500'
                          : 'bg-bg hover:bg-bg-secondary text-text-secondary'
                      }`}
                    >
                      {copyState === 'loading' ? (
                        <Loader2 size={14} className="animate-spin" />
                      ) : copyState === 'copied' ? (
                        <Check size={14} />
                      ) : (
                        <Copy size={14} />
                      )}
                      {copyState === 'loading'
                        ? '转换中...'
                        : copyState === 'copied'
                        ? '已复制'
                        : copyState === 'error'
                        ? '失败'
                        : `复制${config.formatLabel}`}
                    </button>

                    <button
                      onClick={() => handleOpenPlatform(key)}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-bg hover:bg-bg-secondary text-text-secondary transition-all"
                    >
                      <ExternalLink size={14} />
                      发布页
                    </button>
                  </div>
                </div>
              );
            }
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between p-6 border-t border-border bg-white">
          <button
            onClick={handleCopyTitle}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium transition-all ${
              titleCopied
                ? 'bg-success/10 text-success'
                : 'bg-bg hover:bg-bg-secondary text-text-secondary'
            }`}
          >
            {titleCopied ? <Check size={16} /> : <Copy size={16} />}
            {titleCopied ? '标题已复制' : '复制标题'}
          </button>

          <div className="flex items-center gap-3">
            <span className="text-sm text-text-tertiary">
              已选 {selectedPlatforms.size} 个平台
            </span>
            <button
              onClick={handleOpenAll}
              disabled={selectedPlatforms.size === 0}
              className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-medium bg-primary text-white hover:bg-primary/90 disabled:opacity-40 disabled:cursor-not-allowed transition-all"
            >
              <ExternalLink size={16} />
              全部打开
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
