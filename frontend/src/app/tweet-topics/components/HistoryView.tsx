'use client';

import { useState, useEffect } from 'react';
import { Loader2, Trash2, ChevronDown, Brain, Newspaper, ScrollText } from 'lucide-react';
import { extractApiError, tweetTopicsApi } from '@/lib/api';
import type { TweetTopicsRecord } from '@/types/tweet-topics';
import { TopicCard } from './TopicCard';

export function HistoryView() {
  const [records, setRecords] = useState<TweetTopicsRecord[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedRecordId, setExpandedRecordId] = useState<number | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);

  useEffect(() => {
    loadHistory();
  }, []);

  const loadHistory = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await tweetTopicsApi.getHistory();
      setRecords(Array.isArray(response) ? response : []);
    } catch (err) {
      setError(extractApiError(err, '加载历史记录失败'));
    } finally {
      setIsLoading(false);
    }
  };

  const handleDelete = async (recordId: number) => {
    if (!confirm('确定要删除这条记录吗？')) {
      return;
    }

    setDeletingId(recordId);

    try {
      await tweetTopicsApi.deleteRecord(recordId);
      setRecords(records.filter(r => r.id !== recordId));
    } catch (err) {
      setError(extractApiError(err, '删除失败'));
    } finally {
      setDeletingId(null);
    }
  };

  const getModeLabel = (mode: string) => {
    return mode === 'intelligent' ? '🧠 智能模式' : '📰 手动模式';
  };

  const getModeBadgeColor = (mode: string) => {
    return mode === 'intelligent'
      ? 'bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300'
      : 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300';
  };

  const getModeIcon = (mode: string) => {
    return mode === 'intelligent' ? Brain : Newspaper;
  };

  return (
    <div className="space-y-6">
      {/* Page Title and Refresh Button */}
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-semibold text-text-primary flex items-center gap-2">
          <ScrollText size={24} className="text-primary" />
          历史记录
        </h2>
        <button
          onClick={loadHistory}
          disabled={isLoading}
          className="py-2 px-4 bg-bg hover:bg-bg-tertiary text-text-primary rounded-lg transition-colors border border-border flex items-center gap-2"
        >
          {isLoading ? (
            <>
              <Loader2 size={18} className="animate-spin" />
              刷新中...
            </>
          ) : (
            <>🔄 刷新</>
          )}
        </button>
      </div>

      {/* Error Message */}
      {error && (
        <div className="p-4 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400 rounded-lg border border-red-200 dark:border-red-800">
          {error}
        </div>
      )}

      {/* Loading State */}
      {isLoading && records.length === 0 ? (
        <div className="text-center py-12 bg-white rounded-2xl shadow-standard">
          <Loader2 className="animate-spin text-primary mx-auto mb-4" size={48} />
          <p className="text-text-secondary font-medium">加载历史记录中...</p>
        </div>
      ) : records.length === 0 ? (
        <div className="text-center py-12 bg-white rounded-2xl shadow-standard border-2 border-dashed border-border">
          <p className="text-6xl mb-4">📭</p>
          <h3 className="font-heading text-xl font-bold text-text-primary mb-2">
            还没有历史记录
          </h3>
          <p className="text-text-secondary text-sm">
            生成推文选题后会自动保存到这里
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          <p className="text-sm text-text-secondary">
            共 {records.length} 条记录
          </p>

          {records.map(record => {
            const ModeIcon = getModeIcon(record.mode);
            return (
              <div
                key={record.id}
                data-testid={`tweet-topic-history-record-${record.id}`}
                className="bg-white rounded-2xl shadow-sm border border-border/50 overflow-hidden hover:shadow-strong transition-shadow"
              >
                {/* Record Header */}
                <div
                  className="p-4 cursor-pointer hover:bg-bg/30 transition-colors"
                  onClick={() => setExpandedRecordId(
                    expandedRecordId === record.id ? null : record.id
                  )}
                >
                  <div className="flex justify-between items-start gap-4">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2 flex-wrap">
                        <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-lg text-xs font-medium ${getModeBadgeColor(record.mode)}`}>
                          <ModeIcon size={14} />
                          {getModeLabel(record.mode)}
                        </span>
                        {record.topic_name && (
                          <span className="text-sm font-medium text-text-primary flex items-center gap-1">
                            🎯 主题：{record.topic_name}
                          </span>
                        )}
                      </div>
                      <p className="text-sm text-text-secondary">
                        📰 来源：{record.news_source === 'all' ? '全部来源' : record.news_source}
                        {' '}| 📊 {record.news_count}条新闻
                        {' '}| ✨ {record.topics_data.topics?.length || 0}个选题
                        {record.model_name && ` | 🤖 ${record.model_type}/${record.model_name}`}
                      </p>
                      <p className="text-xs text-text-tertiary mt-1">
                        {new Date(record.timestamp).toLocaleString('zh-CN')}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDelete(record.id);
                        }}
                        disabled={deletingId === record.id}
                        aria-label={`删除历史记录 ${record.id}`}
                        data-testid={`tweet-topic-history-delete-${record.id}`}
                        className="py-1 px-3 text-sm bg-red-50 dark:bg-red-900/30 text-red-500 rounded-lg hover:bg-red-100 dark:hover:bg-red-900/50 transition-colors flex items-center gap-1"
                      >
                        {deletingId === record.id ? (
                          <Loader2 size={16} className="animate-spin" />
                        ) : (
                          <Trash2 size={16} />
                        )}
                      </button>
                      <ChevronDown
                        size={24}
                        className={`text-text-tertiary transition-transform ${
                          expandedRecordId === record.id ? 'rotate-180' : ''
                        }`}
                      />
                    </div>
                  </div>

                  {/* Filtered News (Intelligent Mode Only) */}
                  {record.mode === 'intelligent' && record.topics_data.filtered_news && (
                    <div className="mt-3 pt-3 border-t border-border">
                      <details className="text-sm">
                        <summary className="cursor-pointer text-primary hover:text-primary/80">
                          查看筛选的新闻 ({record.topics_data.filtered_news.length}条)
                        </summary>
                        <div className="mt-2 space-y-2">
                          {record.topics_data.filtered_news.map((news, idx) => (
                            <div
                              key={idx}
                              className="p-2 bg-bg/50 rounded-lg text-xs"
                            >
                              <div className="flex justify-between items-start gap-2">
                                <span className="font-medium text-text-primary">{news.title}</span>
                                <span className="text-primary">
                                  相关度: {news.relevance_score}/10
                                </span>
                              </div>
                              <p className="text-text-secondary mt-1">
                                {news.reason}
                              </p>
                            </div>
                          ))}
                        </div>
                      </details>
                    </div>
                  )}
                </div>

                {/* Expanded Topics */}
                {expandedRecordId === record.id && record?.topics_data && (
                  <div className="border-t border-border p-4 space-y-4 bg-bg/20">
                    {/* Summary */}
                    {record.topics_data.summary && (
                      <div className="bg-blue-50 dark:bg-blue-900/20 p-3 rounded-lg border border-blue-100 dark:border-blue-800">
                        <p className="text-sm text-blue-800 dark:text-blue-300">
                          📊 <strong>总结：</strong>{record.topics_data.summary}
                        </p>
                      </div>
                    )}

                    {/* Hot Keywords */}
                    {record.topics_data.hot_keywords && record.topics_data.hot_keywords.length > 0 && (
                      <div className="flex flex-wrap gap-2">
                        {record.topics_data.hot_keywords.map(keyword => (
                          <span
                            key={keyword}
                            className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-primary/10 text-primary"
                          >
                            #{keyword}
                          </span>
                        ))}
                      </div>
                    )}

                    {/* Topic List */}
                    {record.topics_data.topics && record.topics_data.topics.map((topic, index) => (
                      <TopicCard
                        key={index}
                        topic={topic}
                        index={index + 1}
                        newsUrls={record.news_urls}
                      />
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
