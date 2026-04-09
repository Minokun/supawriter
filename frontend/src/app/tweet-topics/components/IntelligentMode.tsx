'use client';

import { useState, useEffect } from 'react';
import { CheckCircle2, Loader2, Plus, Settings } from 'lucide-react';
import { extractApiError, tweetTopicsApi } from '@/lib/api';
import { useCapabilityReadiness } from '@/lib/capability-readiness';
import { CapabilityGate } from '@/components/system/CapabilityGate';
import type { UserTopic, GenerateResponse, TopicDetail } from '@/types/tweet-topics';
import { TopicCard } from './TopicCard';
import { TopicManager } from './TopicManager';

export function IntelligentMode() {
  const readiness = useCapabilityReadiness('writer');
  const [userTopics, setUserTopics] = useState<UserTopic[]>([]);
  const [selectedTopic, setSelectedTopic] = useState<UserTopic | null>(null);
  const [customTopic, setCustomTopic] = useState('');
  const [saveTopic, setSaveTopic] = useState(false);
  const [topicDescription, setTopicDescription] = useState('');
  const [topicCount, setTopicCount] = useState(10);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<GenerateResponse | null>(null);
  const [showTopicManager, setShowTopicManager] = useState(false);
  const [showSuccess, setShowSuccess] = useState(false);

  // Load user topics
  useEffect(() => {
    loadUserTopics();
  }, []);

  // 成功提示3秒后自动消失
  useEffect(() => {
    if (showSuccess) {
      const timer = setTimeout(() => setShowSuccess(false), 3000);
      return () => clearTimeout(timer);
    }
  }, [showSuccess]);

  const loadUserTopics = async () => {
    try {
      const response = await tweetTopicsApi.getUserTopics();
      setUserTopics(response.topics);
    } catch (err) {
      console.error('加载主题失败:', err);
    }
  };

  const handleGenerate = async () => {
    setError(null);
    setResult(null);
    setShowSuccess(false);

    // Validate input
    if (!selectedTopic && !customTopic.trim()) {
      setError('请选择已保存的主题或输入新主题');
      return;
    }

    setIsLoading(true);

    try {
      const response = await tweetTopicsApi.generateIntelligent({
        topic_id: selectedTopic?.id,
        custom_topic: customTopic.trim() || undefined,
        save_topic: saveTopic && customTopic.trim() ? true : false,
        topic_description: topicDescription.trim() || undefined,
        topic_count: topicCount
      });

      setResult(response);
      setShowSuccess(true);

      // If saved new topic, refresh topic list
      if (saveTopic && customTopic.trim()) {
        await loadUserTopics();
      }
    } catch (err) {
      setError(extractApiError(err, '生成失败，请重试'));
    } finally {
      setIsLoading(false);
    }
  };

  const handleSelectTopic = (topic: UserTopic) => {
    setSelectedTopic(topic);
    setCustomTopic('');
  };

  return (
    <div className="space-y-6">
      {/* Topic Selection Area */}
      <div className="bg-white rounded-2xl shadow-standard p-6">
        <h2 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
          <Settings size={20} className="text-primary" />
          选择或输入主题
        </h2>

        {/* Saved Topic Selection */}
        <div className="mb-4">
          <label className="block text-sm font-medium text-text-primary mb-2">
            我的话题
          </label>
          <div className="flex gap-2">
            <select
              value={selectedTopic?.id || ''}
              onChange={(e) => {
                const topic = userTopics.find(t => t.id === Number(e.target.value));
                if (topic) {
                  handleSelectTopic(topic);
                } else {
                  setSelectedTopic(null);
                }
              }}
              className="flex-1 px-4 py-2 bg-bg border border-border rounded-lg text-text-primary focus:ring-2 focus:ring-primary/20 focus:border-primary"
              disabled={isLoading}
            >
              <option value="">选择已保存的话题...</option>
              {userTopics.map(topic => (
                <option key={topic.id} value={topic.id}>
                  {topic.topic_name}
                </option>
              ))}
            </select>
            <button
              type="button"
              onClick={() => setShowTopicManager(true)}
              className="px-4 py-2 bg-bg text-text-primary border border-border rounded-lg hover:bg-bg-tertiary hover:border-primary/30 transition-colors"
              disabled={isLoading}
            >
              管理
            </button>
          </div>
        </div>

        {/* Custom Topic Input */}
        <div className="mb-4">
          <label className="block text-sm font-medium text-text-primary mb-2">
            或输入新主题
          </label>
          <input
            type="text"
            value={customTopic}
            onChange={(e) => {
              setCustomTopic(e.target.value);
              if (e.target.value) {
                setSelectedTopic(null);
              }
            }}
            placeholder="例如：AI与人工智能、前端开发、新能源等"
            className="w-full px-4 py-2 bg-bg border border-border rounded-lg text-text-primary placeholder:text-text-tertiary focus:ring-2 focus:ring-primary/20 focus:border-primary"
            disabled={isLoading}
          />
        </div>

        {/* Save Option */}
        {customTopic.trim() && (
          <div className="mb-4">
            <label className="flex items-center">
              <input
                type="checkbox"
                checked={saveTopic}
                onChange={(e) => setSaveTopic(e.target.checked)}
                className="rounded border-border text-primary focus:ring-primary"
                disabled={isLoading}
              />
              <span className="ml-2 text-sm text-text-primary">
                保存此主题以便下次使用
              </span>
            </label>
            {saveTopic && (
              <textarea
                value={topicDescription}
                onChange={(e) => setTopicDescription(e.target.value)}
                placeholder="可选：添加主题描述..."
                rows={2}
                className="mt-2 w-full px-4 py-2 bg-bg border border-border rounded-lg text-text-primary placeholder:text-text-tertiary focus:ring-2 focus:ring-primary/20 focus:border-primary text-sm"
                disabled={isLoading}
              />
            )}
          </div>
        )}

        {/* Topic Count */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-text-primary mb-2">
            选题数量：{topicCount}个
          </label>
          <input
            type="range"
            min="3"
            max="10"
            value={topicCount}
            onChange={(e) => setTopicCount(Number(e.target.value))}
            className="w-full h-2 bg-bg rounded-lg appearance-none cursor-pointer"
            disabled={isLoading}
          />
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
            <p className="mt-2 text-sm">正在获取新闻并生成选题...</p>
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

      {/* Topic Manager Modal */}
      {showTopicManager && (
        <TopicManager
          topics={userTopics}
          onClose={() => setShowTopicManager(false)}
          onUpdate={loadUserTopics}
          onSelectTopic={handleSelectTopic}
        />
      )}
    </div>
  );
}
