'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { ChevronDown, ChevronUp, Lock, TrendingUp, RefreshCw } from 'lucide-react';
import { historyApi, ArticleScoreResponse, ScoreDimension } from '@/types/api';
import { useAuth } from '@/hooks/useAuth';

interface ScoreCardProps {
  articleId?: string;
  isLoading?: boolean;
}

// 评分缓存工具
const SCORE_CACHE_PREFIX = 'score_cache_';
const SCORE_CACHE_EXPIRY = 24 * 60 * 60 * 1000; // 24小时过期

interface CachedScore {
  data: ArticleScoreResponse;
  timestamp: number;
}

const getCachedScore = (articleId: string): ArticleScoreResponse | null => {
  try {
    const cached = localStorage.getItem(SCORE_CACHE_PREFIX + articleId);
    if (!cached) return null;
    const parsed: CachedScore = JSON.parse(cached);
    // 检查是否过期
    if (Date.now() - parsed.timestamp > SCORE_CACHE_EXPIRY) {
      localStorage.removeItem(SCORE_CACHE_PREFIX + articleId);
      return null;
    }
    return parsed.data;
  } catch {
    return null;
  }
};

const setCachedScore = (articleId: string, data: ArticleScoreResponse) => {
  try {
    const cache: CachedScore = {
      data,
      timestamp: Date.now()
    };
    localStorage.setItem(SCORE_CACHE_PREFIX + articleId, JSON.stringify(cache));
  } catch (e) {
    console.warn('Failed to cache score:', e);
  }
};

const clearScoreCache = (articleId: string) => {
  try {
    localStorage.removeItem(SCORE_CACHE_PREFIX + articleId);
  } catch {}
};

const LEVEL_COLORS: Record<string, string> = {
  excellent: 'text-green-600 bg-green-50',
  good: 'text-blue-600 bg-blue-50',
  average: 'text-yellow-600 bg-yellow-50',
  poor: 'text-red-600 bg-red-50',
};

const LEVEL_LABELS: Record<string, string> = {
  excellent: '优秀 🌟',
  good: '良好 👍',
  average: '一般 ⚖️',
  poor: '需改进 ⚠️',
};

const DIMENSION_COLORS: Record<number, string> = {
  85: 'bg-green-500',
  70: 'bg-blue-500',
  50: 'bg-yellow-500',
  0: 'bg-red-500',
};

export function ScoreCard({ articleId, isLoading: externalLoading }: ScoreCardProps) {
  const router = useRouter();
  const { userInfo } = useAuth();
  const [score, setScore] = useState<ArticleScoreResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const userTier = userInfo?.membership_tier || 'free';

  const isPro = userTier === 'pro' || userTier === 'ultra' || userTier === 'superuser';

  // 从缓存或API加载评分
  useEffect(() => {
    if (articleId) {
      // 先尝试从缓存加载
      const cached = getCachedScore(articleId);
      if (cached) {
        setScore(cached);
      } else {
        loadScore();
      }
    }
  }, [articleId]);

  const loadScore = useCallback(async (forceRefresh = false) => {
    if (!articleId) return;

    // 如果不是强制刷新，先检查缓存
    if (!forceRefresh) {
      const cached = getCachedScore(articleId);
      if (cached) {
        setScore(cached);
        return;
      }
    }

    setLoading(true);
    setError(null);
    try {
      const result = await historyApi.getArticleScore(articleId);
      setScore(result);
      // 缓存结果
      setCachedScore(articleId, result);
    } catch (err) {
      setError(err instanceof Error ? err.message : '评分加载失败');
      console.error('Failed to load score:', err);
    } finally {
      setLoading(false);
      setIsRefreshing(false);
    }
  }, [articleId]);

  // 强制刷新评分
  const handleRefresh = () => {
    if (!articleId) return;
    setIsRefreshing(true);
    clearScoreCache(articleId);
    loadScore(true);
  };

  const getProgressColor = (scoreValue: number): string => {
    if (scoreValue >= 85) return DIMENSION_COLORS[85];
    if (scoreValue >= 70) return DIMENSION_COLORS[70];
    if (scoreValue >= 50) return DIMENSION_COLORS[50];
    return DIMENSION_COLORS[0];
  };

  const getLevelClass = (level: string): string => {
    return LEVEL_COLORS[level] || LEVEL_COLORS.poor;
  };

  // 在加载状态下显示
  if (externalLoading || loading) {
    return (
      <div className="border border-border rounded-lg p-6 bg-white">
        <div className="flex items-center justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
          <span className="ml-3 text-text-secondary">正在评分...</span>
        </div>
      </div>
    );
  }

  // 在错误状态下显示
  if (error) {
    return (
      <div className="border border-border rounded-lg p-6 bg-white">
        <div className="flex items-center justify-center py-8">
          <span className="text-error">{error}</span>
        </div>
      </div>
    );
  }

  // 如果没有分数数据，不显示任何内容
  if (!score) {
    return null;
  }

  // 正常显示评分卡片
  return (
    <div className="border border-border rounded-lg overflow-hidden bg-white shadow-sm">
      {/* Header - 评分摘要部分 */}
      <div
        className="p-6 cursor-pointer transition-colors hover:bg-bg-secondary"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            {/* 总分显示 - 圆形进度图 */}
            <div className="relative">
              <div className="w-24 h-24 rounded-full border-8 border-gray-100 flex items-center justify-center">
                <div className="text-center">
                  <div className="text-3xl font-bold text-text-primary">
                    {score.total_score}
                  </div>
                  <div className="text-xs text-text-tertiary">/ 100</div>
                </div>
              </div>
              {/* 等级标签 */}
              <div className={`absolute -bottom-2 -right-2 px-3 py-1 rounded-full text-xs font-medium ${getLevelClass(score.level)}`}>
                {LEVEL_LABELS[score.level] || score.level}
              </div>
            </div>

            {/* 评语和时间 */}
            <div className="flex flex-col">
              <span className="text-sm font-medium text-text-primary">
                {score.summary}
              </span>
              <span className="text-xs text-text-tertiary mt-1">
                评分时间: {new Date(score.scored_at).toLocaleString('zh-CN')}
              </span>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* 刷新按钮 */}
            <button
              onClick={(e) => {
                e.stopPropagation();
                handleRefresh();
              }}
              disabled={isRefreshing || loading}
              className="p-2 hover:bg-bg-tertiary rounded-lg transition-colors disabled:opacity-50"
              title="刷新评分"
            >
              <RefreshCw size={18} className={`text-text-secondary ${isRefreshing || loading ? 'animate-spin' : ''}`} />
            </button>
            {/* 展开/折叠按钮 */}
            <button className="p-2 hover:bg-bg-tertiary rounded-lg transition-colors">
              {expanded ? (
                <ChevronUp size={20} className="text-text-secondary" />
              ) : (
                <ChevronDown size={20} className="text-text-secondary" />
              )}
            </button>
          </div>
        </div>
      </div>

      {/* 详细评分（仅Pro用户）- 可展开/折叠 */}
      {expanded && (
        <div className="border-t border-border bg-bg-secondary">
          {isPro ? (
            // Pro用户 - 显示详细评分
            <div className="p-6 space-y-4">
              {score.dimensions.map((dimension) => (
                <div key={dimension.name} className="space-y-2">
                  {/* 维度名称和分数 */}
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-text-primary">
                      {dimension.label}
                    </span>
                    <span className="font-semibold text-text-primary">
                      {dimension.score}分
                    </span>
                  </div>

                  {/* 进度条 */}
                  <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                    <div
                      className={`h-full transition-all duration-500 ${getProgressColor(dimension.score)}`}
                      style={{ width: `${dimension.score}%` }}
                    />
                  </div>

                  {/* 权重说明 */}
                  <div className="flex items-center gap-2">
                    <TrendingUp size={14} className="text-text-tertiary" />
                    <span className="text-xs text-text-tertiary">
                      权重 {(dimension.weight * 100).toFixed(0)}%
                    </span>
                  </div>

                  {/* 优化建议 - 如果存在的话 */}
                  {dimension.suggestions && dimension.suggestions.length > 0 && (
                    <div className="mt-3 p-3 bg-white rounded-lg border border-border">
                      <div className="text-sm font-medium text-text-primary mb-2">
                        💡 优化建议
                      </div>
                      <ul className="space-y-1">
                        {dimension.suggestions.map((suggestion, idx) => (
                          <li key={idx} className="text-sm text-text-secondary flex items-start">
                            <span className="mr-2 text-primary">•</span>
                            <span>{suggestion}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            // Free用户 - 显示升级引导
            <div className="p-8 text-center">
              <div className="inline-flex items-center justify-center w-16 h-16 bg-orange-100 rounded-full mb-4">
                <Lock size={32} className="text-orange-600" />
              </div>
              <h3 className="text-lg font-semibold text-text-primary mb-2">
                🔒 升级 Pro 查看详细评分
              </h3>
              <p className="text-sm text-text-secondary mb-4 max-w-md mx-auto">
                获取详细的多维度评分分析，包括可读性、信息密度、SEO友好度和传播力分析
              </p>
              <button
                onClick={() => router.push('/pricing')}
                className="px-6 py-2 bg-primary text-white rounded-lg hover:bg-primary/90 transition-colors"
              >
                立即升级
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
