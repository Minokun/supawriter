'use client';

import { useState, useEffect } from 'react';
import { CheckCircle2, Loader2, Newspaper, Radio, Waves, Zap } from 'lucide-react';
import { extractApiError, tweetTopicsApi } from '@/lib/api';
import { useCapabilityReadiness } from '@/lib/capability-readiness';
import { CapabilityGate } from '@/components/system/CapabilityGate';
import type { GenerateResponse, TopicDetail } from '@/types/tweet-topics';
import { TopicCard } from './TopicCard';

const NEWS_SOURCES = [
  { id: '澎湃科技', name: '澎湃科技', icon: Newspaper, color: 'bg-blue-50 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400' },
  { id: 'SOTA开源项目', name: 'SOTA开源项目', icon: Zap, color: 'bg-purple-50 text-purple-600 dark:bg-purple-900/30 dark:text-purple-400' },
  { id: '实时新闻', name: '实时新闻', icon: Radio, color: 'bg-green-50 text-green-600 dark:bg-green-900/30 dark:text-green-400' },
  { id: '新浪直播', name: '新浪直播', icon: Waves, color: 'bg-orange-50 text-orange-600 dark:bg-orange-900/30 dark:text-orange-400' }
];

export function ManualMode() {
  const readiness = useCapabilityReadiness('writer');
  const [selectedSource, setSelectedSource] = useState('澎湃科技');
  const [newsCount, setNewsCount] = useState(15);
  const [topicCount, setTopicCount] = useState(8);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<GenerateResponse | null>(null);
  const [showSuccess, setShowSuccess] = useState(false);

  const handleGenerate = async () => {
    setError(null);
    setResult(null);
    setShowSuccess(false);
    setIsLoading(true);

    try {
      const response = await tweetTopicsApi.generateManual({
        news_source: selectedSource,
        news_count: newsCount,
        topic_count: topicCount
      });

      setResult(response);
      setShowSuccess(true);
    } catch (err) {
      setError(extractApiError(err, '生成失败，请重试'));
    } finally {
      setIsLoading(false);
    }
  };

  // 成功提示3秒后自动消失
  useEffect(() => {
    if (showSuccess) {
      const timer = setTimeout(() => setShowSuccess(false), 3000);
      return () => clearTimeout(timer);
    }
  }, [showSuccess]);

  const selectedSourceData = NEWS_SOURCES.find(s => s.id === selectedSource);
  const SelectedIcon = selectedSourceData?.icon || Newspaper;

  return (
    <div className="space-y-6">
      {/* Configuration Area */}
      <div className="bg-white rounded-2xl shadow-standard p-6">
        <h2 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
          <Newspaper size={20} className="text-primary" />
          选择新闻源
        </h2>

        {/* News Source Selection */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
          {NEWS_SOURCES.map(source => {
            const Icon = source.icon;
            return (
              <button
                key={source.id}
                onClick={() => setSelectedSource(source.id)}
                className={`p-4 rounded-xl border-2 transition-all ${
                  selectedSource === source.id
                    ? 'border-primary bg-primary/5 shadow-md'
                    : 'border-border hover:border-primary/30 hover:bg-bg'
                }`}
                disabled={isLoading}
              >
                <div className={`w-10 h-10 mx-auto mb-2 rounded-lg ${source.color} flex items-center justify-center`}>
                  <Icon size={24} />
                </div>
                <div className="text-sm font-medium text-text-primary">
                  {source.name}
                </div>
              </button>
            );
          })}
        </div>

        {/* Parameter Settings */}
        <div className="grid md:grid-cols-2 gap-6 mb-6">
          {/* News Count */}
          <div>
            <label className="block text-sm font-medium text-text-primary mb-2">
              获取新闻数量：{newsCount}条
            </label>
            <input
              type="range"
              min="5"
              max="30"
              step="5"
              value={newsCount}
              onChange={(e) => setNewsCount(Number(e.target.value))}
              className="w-full h-2 bg-bg rounded-lg appearance-none cursor-pointer"
              disabled={isLoading}
            />
          </div>

          {/* Topic Count */}
          <div>
            <label className="block text-sm font-medium text-text-primary mb-2">
              生成选题数量：{topicCount}个
            </label>
            <input
              type="range"
              min="3"
              max="15"
              value={topicCount}
              onChange={(e) => setTopicCount(Number(e.target.value))}
              className="w-full h-2 bg-bg rounded-lg appearance-none cursor-pointer"
              disabled={isLoading}
            />
          </div>
        </div>

        {/* Current Configuration Display */}
        <div className="bg-bg/50 rounded-xl p-4 mb-6 border border-border/50">
          <p className="text-sm text-text-primary flex items-center gap-2">
            <SelectedIcon size={18} className="text-primary" />
            <span>当前配置：</span>
            <strong className="text-primary">{selectedSourceData?.name}</strong>
            {' '}| 获取 <strong>{newsCount}条</strong> 新闻
            {' '}| 生成 <strong>{topicCount}个</strong> 选题
          </p>
        </div>

        {/* Generate Button */}
        {!readiness.ready && !readiness.loading && (
          <div className="mb-4">
            <CapabilityGate
              title={readiness.title}
              description={readiness.description}
              ctaHref={readiness.ctaHref}
              ctaLabel={readiness.ctaLabel}
            />
          </div>
        )}
        <button
          onClick={handleGenerate}
          disabled={isLoading || !readiness.ready}
          className="w-full py-3 px-4 bg-primary hover:bg-primary/90 disabled:bg-text-tertiary text-white font-medium rounded-lg transition-colors flex items-center justify-center gap-2"
        >
          {isLoading ? (
            <>
              <Loader2 size={20} className="animate-spin" />
              生成中...
            </>
          ) : (
            <>🚀 开始生成</>
          )}
        </button>

        {/* Success Message */}
        {showSuccess && (
          <div className="mt-4 p-4 bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-400 rounded-lg border border-green-200 dark:border-green-800 flex items-center gap-3 animate-in fade-in slide-in-from-bottom-2 duration-300">
            <CheckCircle2 size={20} className="flex-shrink-0" />
            <p className="font-medium">
              ✓ 选题生成成功！已生成 {result?.topics_data?.topics?.length || 0} 个选题
            </p>
          </div>
        )}

        {/* Error Message */}
        {error && (
          <div className="mt-4 p-4 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400 rounded-lg border border-red-200 dark:border-red-800">
            {error}
          </div>
        )}

        {/* Loading State */}
        {isLoading && (
          <div className="mt-4 text-center text-text-secondary">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
            <p className="mt-2 text-sm">正在从 {selectedSourceData?.name} 获取新闻...</p>
          </div>
        )}
      </div>

      {/* Generation Results */}
      {result && (
        <div className="space-y-4">
          {/* Summary */}
          {result?.topics_data?.summary && (
            <div className="bg-blue-50 dark:bg-blue-900/20 p-4 rounded-lg border border-blue-100 dark:border-blue-800">
              <p className="text-blue-800 dark:text-blue-300 text-sm">
                📊 <strong>选题总结：</strong>{result.topics_data.summary}
              </p>
            </div>
          )}

          {/* Hot Keywords */}
          {result?.topics_data?.hot_keywords && result.topics_data.hot_keywords.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {result.topics_data.hot_keywords.map(keyword => (
                <span
                  key={keyword}
                  className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-primary/10 text-primary"
                >
                  #{keyword}
                </span>
              ))}
            </div>
          )}

          {/* Topic Cards */}
          {result?.topics_data?.topics && result.topics_data.topics.map((topic, index) => (
            <TopicCard
              key={index}
              topic={topic}
              index={index + 1}
              newsUrls={result.news_urls}
            />
          ))}
        </div>
      )}
    </div>
  );
}
