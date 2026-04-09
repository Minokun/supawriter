'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import {
  Search,
  Copy,
  Check,
  X,
  TrendingUp,
  Lock,
  Sparkles,
  ChevronDown,
  ChevronUp,
  Link as LinkIcon,
  AlertCircle,
  RefreshCw
} from 'lucide-react';
import { historyApi, SEOAnalysisResponse } from '@/types/api';
import { useAuth } from '@/hooks/useAuth';

interface SEOPanelProps {
  content: string;
  title?: string;
  articleId?: string;
  onApplyTitle?: (title: string) => void;
  onCopyMeta?: (description: string) => void;
}

// SEO 缓存工具
const SEO_CACHE_PREFIX = 'seo_cache_';
const SEO_CACHE_EXPIRY = 30 * 60 * 1000; // 30分钟过期

interface CachedSEO {
  data: SEOAnalysisResponse;
  timestamp: number;
  contentHash: string;
}

// 生成内容简单哈希用于缓存键
const hashContent = (content: string, title: string): string => {
  return content.slice(0, 200) + title.slice(0, 50);
};

const getCachedSEO = (articleId: string | undefined, contentHash: string): SEOAnalysisResponse | null => {
  try {
    const key = SEO_CACHE_PREFIX + (articleId || contentHash.slice(0, 50));
    const cached = localStorage.getItem(key);
    if (!cached) return null;
    const parsed: CachedSEO = JSON.parse(cached);
    // 检查是否过期
    if (Date.now() - parsed.timestamp > SEO_CACHE_EXPIRY) {
      localStorage.removeItem(key);
      return null;
    }
    // 检查内容是否匹配
    if (parsed.contentHash !== contentHash) {
      return null;
    }
    return parsed.data;
  } catch {
    return null;
  }
};

const setCachedSEO = (articleId: string | undefined, contentHash: string, data: SEOAnalysisResponse) => {
  try {
    const key = SEO_CACHE_PREFIX + (articleId || contentHash.slice(0, 50));
    const cache: CachedSEO = {
      data,
      timestamp: Date.now(),
      contentHash
    };
    localStorage.setItem(key, JSON.stringify(cache));
  } catch (e) {
    console.warn('Failed to cache SEO:', e);
  }
};

const clearSEOCache = (articleId: string | undefined, contentHash: string) => {
  try {
    const key = SEO_CACHE_PREFIX + (articleId || contentHash.slice(0, 50));
    localStorage.removeItem(key);
  } catch {}
};

const LEVEL_COLORS: Record<string, string> = {
  excellent: 'text-green-600 bg-green-50',
  good: 'text-blue-600 bg-blue-50',
  average: 'text-yellow-600 bg-yellow-50',
  poor: 'text-red-600 bg-red-50'
};

const DENSITY_COLORS: Record<string, string> = {
  good: 'text-green-600 bg-green-50',
  acceptable: 'text-yellow-600 bg-yellow-50',
  low: 'text-red-600 bg-red-50',
  high: 'text-orange-600 bg-orange-50'
};

export function SEOPanel({
  content,
  title = '',
  articleId,
  onApplyTitle,
  onCopyMeta
}: SEOPanelProps) {
  const router = useRouter();
  const { userInfo } = useAuth();
  const [seoData, setSeoData] = useState<SEOAnalysisResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedSection, setExpandedSection] = useState<string | null>('keywords');
  const [copiedText, setCopiedText] = useState<string | null>(null);
  const userTier = userInfo?.membership_tier || 'free';

  const isPro = userTier === 'pro' || userTier === 'ultra' || userTier === 'superuser';
  const [isRefreshing, setIsRefreshing] = useState(false);

  // 生成内容哈希
  const contentHash = hashContent(content, title || '');

  useEffect(() => {
    if (content && content.length > 50) {
      // 先尝试从缓存加载
      const cached = getCachedSEO(articleId, contentHash);
      if (cached) {
        setSeoData(cached);
      } else {
        analyzeSEO(false);
      }
    }
  }, [content, title, articleId]);

  const analyzeSEO = useCallback(async (forceRefresh = false) => {
    if (!content || content.length < 50) {
      setError('文章内容过短，请至少输入50个字符');
      return;
    }

    // 如果不是强制刷新，先检查缓存
    if (!forceRefresh) {
      const cached = getCachedSEO(articleId, contentHash);
      if (cached) {
        setSeoData(cached);
        return;
      }
    }

    setLoading(true);
    setError(null);
    try {
      const result = await historyApi.analyzeSEO(content, title, articleId);
      setSeoData(result);
      // 缓存结果
      setCachedSEO(articleId, contentHash, result);
    } catch (err) {
      if (err instanceof Error && err.message.includes('Pro及以上会员')) {
        setError('SEO分析功能需要Pro及以上会员');
      } else {
        setError(err instanceof Error ? err.message : 'SEO分析失败');
        console.error('Failed to analyze SEO:', err);
      }
    } finally {
      setLoading(false);
      setIsRefreshing(false);
    }
  }, [content, title, articleId, contentHash]);

  // 强制刷新SEO分析
  const handleRefresh = () => {
    setIsRefreshing(true);
    clearSEOCache(articleId, contentHash);
    analyzeSEO(true);
  };

  const getDensityClass = (status: string): string => {
    return DENSITY_COLORS[status] || DENSITY_COLORS.low;
  };

  const getProgressColor = (score: number): string => {
    if (score >= 85) return 'bg-green-500';
    if (score >= 70) return 'bg-blue-500';
    if (score >= 50) return 'bg-yellow-500';
    return 'bg-red-500';
  };

  const handleCopy = (text: string, type: string) => {
    navigator.clipboard.writeText(text);
    setCopiedText(type);
    setTimeout(() => setCopiedText(null), 2000);
  };

  const handleApplyTitle = (newTitle: string) => {
    if (onApplyTitle) {
      onApplyTitle(newTitle);
    }
  };

  if (loading) {
    return (
      <div className="border border-border rounded-lg p-6 bg-white">
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
          <span className="ml-3 text-text-secondary">正在分析SEO...</span>
        </div>
      </div>
    );
  }

  if (!isPro) {
    return (
      <div className="border border-border rounded-lg p-8 bg-white">
        <div className="text-center">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-orange-100 rounded-full mb-4">
            <Lock size={32} className="text-orange-600" />
          </div>
          <h3 className="text-lg font-semibold text-text-primary mb-2">
            🔒 SEO分析需要Pro会员
          </h3>
          <p className="text-sm text-text-secondary mb-6 max-w-md mx-auto">
            获取专业的SEO分析，包括关键词提取、标题优化、元描述生成和内链建议
          </p>
          <button
            onClick={() => router.push('/pricing')}
            className="px-6 py-2 bg-primary text-white rounded-lg hover:bg-primary/90 transition-colors"
          >
            立即升级
          </button>
        </div>
      </div>
    );
  }

  if (!seoData) {
    return (
      <div className="border border-border rounded-lg p-8 bg-white">
        <div className="text-center">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-gray-100 rounded-full mb-4">
            <Search size={32} className="text-gray-400" />
          </div>
          <h3 className="text-lg font-semibold text-text-primary mb-2">
            SEO分析
          </h3>
          <p className="text-sm text-text-secondary mb-4 max-w-md mx-auto">
            输入文章内容和标题后，系统将自动进行SEO分析
          </p>
          <button
            onClick={() => analyzeSEO(false)}
            disabled={!content || content.length < 50 || loading}
            className="px-6 py-2 bg-primary text-white rounded-lg hover:bg-primary/90 transition-colors disabled:bg-gray-300 disabled:cursor-not-allowed"
          >
            {loading ? '分析中...' : '开始分析'}
          </button>
          <p className="text-xs text-text-tertiary mt-4">
            {content?.length || 0} / 50 字符
          </p>
        </div>
      </div>
    );
  }

  const { seo_score, keywords, title_optimization, meta_description, internal_links } = seoData;

  return (
    <div className="border border-border rounded-lg overflow-hidden bg-white shadow-sm">
      {/* Header - 总体评分 */}
      <div className="p-6 border-b border-border bg-gradient-to-r from-blue-50 to-purple-50">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            {/* 评分圆环 */}
            <div className="relative">
              <div className="w-20 h-20 rounded-full border-4 border-white bg-white flex items-center justify-center shadow-lg">
                <div className="text-center">
                  <div className="text-2xl font-bold text-text-primary">
                    {seo_score.score}
                  </div>
                  <div className="text-xs text-text-tertiary">/ 100</div>
                </div>
              </div>
              {/* 等级标签 */}
              <div className={`absolute -bottom-1 -right-1 px-2 py-0.5 rounded-full text-xs font-medium ${LEVEL_COLORS[seo_score.level]}`}>
                {seo_score.level_label}
              </div>
            </div>

            {/* 评语 */}
            <div className="flex flex-col">
              <span className="font-semibold text-text-primary text-sm">
                SEO综合评分
              </span>
              <div className="flex flex-wrap gap-1 mt-1">
                {seo_score.feedback.slice(0, 2).map((feedback, idx) => (
                  <span
                    key={idx}
                    className="text-xs px-2 py-0.5 bg-white/60 rounded-md text-text-secondary"
                  >
                    {feedback}
                  </span>
                ))}
              </div>
            </div>
          </div>

          {/* 刷新按钮 */}
          <button
            onClick={handleRefresh}
            disabled={isRefreshing || loading}
            className="p-2 hover:bg-white rounded-lg transition-colors disabled:opacity-50"
            title="重新分析"
          >
            <RefreshCw size={18} className={`text-text-secondary ${isRefreshing || loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* 关键词分析 */}
      <SEOSection
        title="关键词分析"
        icon={<Search size={18} />}
        isExpanded={expandedSection === 'keywords'}
        onToggle={() => setExpandedSection(expandedSection === 'keywords' ? null : 'keywords')}
      >
        <div className="space-y-3">
          {keywords.map((kw, idx) => (
            <div key={idx} className="border border-border rounded-lg p-3">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <span className="font-medium text-text-primary">{kw.keyword}</span>
                  <span className="text-xs px-2 py-0.5 bg-blue-100 text-blue-700 rounded-full">
                    相关性 {kw.relevance}
                  </span>
                </div>
                <span className={`text-sm font-semibold ${getDensityClass(kw.density.status)}`}>
                  {kw.density.density}%
                </span>
              </div>

              {/* 密度条 */}
              <div className="h-2 bg-gray-100 rounded-full overflow-hidden mb-2">
                <div
                  className={`h-full ${kw.density.status === 'good' ? 'bg-green-500' : kw.density.status === 'acceptable' ? 'bg-yellow-500' : 'bg-red-500'}`}
                  style={{ width: `${Math.min(kw.density.density * 10, 100)}%` }}
                />
              </div>

              {/* 详细信息 */}
              <div className="flex items-center gap-4 text-xs text-text-tertiary">
                <span>出现 {kw.density.count} 次</span>
                <span className={`px-2 py-0.5 rounded ${getDensityClass(kw.density.status)}`}>
                  {kw.density.suggestion}
                </span>
              </div>
            </div>
          ))}

          <div className="text-xs text-text-tertiary mt-2">
            💡 关键词密度2-3.5%为最佳，过低可能影响搜索排名，过高可能被视为关键词堆砌
          </div>
        </div>
      </SEOSection>

      {/* 标题优化 */}
      <SEOSection
        title="标题优化"
        icon={<Sparkles size={18} />}
        isExpanded={expandedSection === 'title'}
        onToggle={() => setExpandedSection(expandedSection === 'title' ? null : 'title')}
      >
        <div className="space-y-4">
          {/* 当前标题评分 */}
          <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
            <div>
              <span className="text-sm text-text-tertiary mb-1 block">当前标题</span>
              <span className="font-medium text-text-primary">{title_optimization.current_title || '未设置'}</span>
            </div>
            <div className="text-right">
              <div className="text-2xl font-bold text-text-primary">{title_optimization.score}</div>
              <div className="text-xs text-text-tertiary">/ 100</div>
            </div>
          </div>

          {/* 评语 */}
          <div className="p-3 bg-blue-50 rounded-lg text-sm text-blue-800">
            {title_optimization.feedback}
          </div>

          {/* 优化建议 */}
          {title_optimization.suggestions && title_optimization.suggestions.length > 0 && (
            <div className="space-y-2">
              <div className="text-sm font-medium text-text-primary">
                💡 优化建议
              </div>
              {title_optimization.suggestions.map((suggestion, idx) => (
                <div key={idx} className="p-3 border border-border rounded-lg hover:border-primary transition-colors">
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1">
                      <div className="font-medium text-text-primary text-sm mb-1">
                        {suggestion.title}
                      </div>
                      <div className="text-xs text-text-tertiary">
                        {suggestion.reason}
                      </div>
                    </div>
                    <button
                      onClick={() => handleApplyTitle(suggestion.title)}
                      className="p-2 bg-primary text-white rounded-lg hover:bg-primary/90 transition-colors shrink-0"
                      title="应用此标题"
                    >
                      <Check size={16} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </SEOSection>

      {/* 元描述生成 */}
      <SEOSection
        title="元描述"
        icon={<TrendingUp size={18} />}
        isExpanded={expandedSection === 'meta'}
        onToggle={() => setExpandedSection(expandedSection === 'meta' ? null : 'meta')}
      >
        <div className="space-y-4">
          {/* 生成的描述 */}
          <div className="p-4 bg-gray-50 rounded-lg">
            <div className="flex items-start justify-between gap-2">
              <div className="flex-1">
                <div className="text-sm font-medium text-text-primary mb-2">
                  生成的元描述（{meta_description.length} 字符）
                </div>
                <p className="text-sm text-text-secondary leading-relaxed">
                  {meta_description.description}
                </p>
              </div>
              <button
                onClick={() => handleCopy(meta_description.description, 'meta')}
                className="p-2 hover:bg-white rounded-lg transition-colors shrink-0"
                title="复制描述"
              >
                {copiedText === 'meta' ? (
                  <Check size={16} className="text-green-600" />
                ) : (
                  <Copy size={16} className="text-text-secondary" />
                )}
              </button>
            </div>
          </div>

          {/* 状态指示 */}
          <div className={`p-3 rounded-lg text-sm ${getDensityClass(meta_description.status)}`}>
            <div className="flex items-center gap-2">
              {meta_description.status === 'good' ? (
                <Check size={16} />
              ) : (
                <AlertCircle size={16} />
              )}
              <span>{meta_description.suggestion}</span>
            </div>
          </div>

          {/* 长度指示条 */}
          <div>
            <div className="flex items-center justify-between text-xs text-text-tertiary mb-1">
              <span>120</span>
              <span>理想范围</span>
              <span>160</span>
            </div>
            <div className="h-2 bg-gray-200 rounded-full overflow-hidden relative">
              <div
                className={`absolute h-full ${meta_description.status === 'good' ? 'bg-green-500' : meta_description.status === 'acceptable' ? 'bg-yellow-500' : 'bg-red-500'}`}
                style={{
                  left: `${((meta_description.length - 120) / 40) * 100}%`,
                  width: '2px'
                }}
              />
            </div>
          </div>
        </div>
      </SEOSection>

      {/* 内链建议 */}
      {internal_links && internal_links.length > 0 && (
        <SEOSection
          title="内链建议"
          icon={<LinkIcon size={18} />}
          isExpanded={expandedSection === 'links'}
          onToggle={() => setExpandedSection(expandedSection === 'links' ? null : 'links')}
        >
          <div className="space-y-2">
            {internal_links.map((link, idx) => (
              <div key={idx} className="p-3 border border-border rounded-lg hover:border-primary transition-colors">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1">
                    <div className="font-medium text-text-primary text-sm mb-1">
                      {link.title}
                    </div>
                    <div className="flex items-center gap-2 text-xs text-text-tertiary">
                      <span className="px-2 py-0.5 bg-blue-100 text-blue-700 rounded-full">
                        相关性 {link.relevance}
                      </span>
                      <span>{link.reason}</span>
                    </div>
                    {link.suggested_anchor_text && (
                      <div className="mt-2 text-xs text-text-tertiary">
                        建议锚文本: <span className="text-primary font-medium">&ldquo;{link.suggested_anchor_text}&rdquo;</span>
                      </div>
                    )}
                  </div>
                  <button
                    onClick={() => handleCopy(link.suggested_anchor_text || link.title, `link-${idx}`)}
                    className="p-2 hover:bg-gray-100 rounded-lg transition-colors shrink-0"
                    title="复制链接文本"
                  >
                    {copiedText === `link-${idx}` ? (
                      <Check size={16} className="text-green-600" />
                    ) : (
                      <Copy size={16} className="text-text-secondary" />
                    )}
                  </button>
                </div>
              </div>
            ))}
          </div>
        </SEOSection>
      )}
    </div>
  );
}

// 子组件：可折叠的SEO部分
interface SEOSectionProps {
  title: string;
  icon: React.ReactNode;
  isExpanded: boolean;
  onToggle: () => void;
  children: React.ReactNode;
}

function SEOSection({ title, icon, isExpanded, onToggle, children }: SEOSectionProps) {
  return (
    <div className="border-b border-border last:border-b-0">
      <button
        onClick={onToggle}
        className="w-full p-4 flex items-center justify-between text-left hover:bg-bg-secondary transition-colors"
      >
        <div className="flex items-center gap-2">
          {icon}
          <span className="font-medium text-text-primary">{title}</span>
        </div>
        {isExpanded ? (
          <ChevronUp size={18} className="text-text-secondary" />
        ) : (
          <ChevronDown size={18} className="text-text-secondary" />
        )}
      </button>

      {isExpanded && <div className="p-4 pt-0">{children}</div>}
    </div>
  );
}
