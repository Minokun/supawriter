'use client';

import { useState } from 'react';
import { X, Plus, Trash2, Check } from 'lucide-react';
import { tweetTopicsApi } from '@/lib/api';
import type { UserTopic } from '@/types/tweet-topics';

interface TopicManagerProps {
  topics: UserTopic[];
  onClose: () => void;
  onUpdate: () => void;
  onSelectTopic?: (topic: UserTopic) => void;
}

export function TopicManager({ topics, onClose, onUpdate, onSelectTopic }: TopicManagerProps) {
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newTopicName, setNewTopicName] = useState('');
  const [newTopicDesc, setNewTopicDesc] = useState('');
  const [isCreating, setIsCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [localTopics, setLocalTopics] = useState(topics);

  const handleCreate = async () => {
    if (!newTopicName.trim()) {
      setError('请输入主题名称');
      return;
    }

    setIsCreating(true);
    setError(null);

    try {
      await tweetTopicsApi.createUserTopic({
        topic_name: newTopicName.trim(),
        description: newTopicDesc.trim() || undefined
      });

      setNewTopicName('');
      setNewTopicDesc('');
      setShowCreateForm(false);
      await onUpdate();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '创建失败');
    } finally {
      setIsCreating(false);
    }
  };

  const handleDelete = async (topicId: number) => {
    if (!confirm('确定要删除这个主题吗？')) {
      return;
    }

    try {
      await tweetTopicsApi.deleteUserTopic(topicId);
      setLocalTopics(localTopics.filter(t => t.id !== topicId));
      await onUpdate();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '删除失败');
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4 animate-in fade-in duration-200">
      <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl max-w-2xl w-full max-h-[80vh] overflow-hidden flex flex-col animate-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="flex justify-between items-center p-6 border-b border-border bg-white/50">
          <h2 className="text-xl font-bold text-text-primary flex items-center gap-2">
            📌 我的话题
          </h2>
          <button
            onClick={onClose}
            className="text-text-tertiary hover:text-text-primary transition-colors"
          >
            <X size={24} />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {/* Create Topic Form */}
          {showCreateForm ? (
            <div className="mb-6 p-4 bg-bg/50 rounded-xl border border-border">
              <h3 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
                <Plus size={18} className="text-primary" />
                新建主题
              </h3>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-text-primary mb-1">
                    主题名称 *
                  </label>
                  <input
                    type="text"
                    value={newTopicName}
                    onChange={(e) => setNewTopicName(e.target.value)}
                    placeholder="例如：AI与人工智能"
                    className="w-full px-4 py-2 bg-white border border-border rounded-lg text-text-primary placeholder:text-text-tertiary focus:ring-2 focus:ring-primary/20 focus:border-primary"
                    disabled={isCreating}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-text-primary mb-1">
                    描述（可选）
                  </label>
                  <textarea
                    value={newTopicDesc}
                    onChange={(e) => setNewTopicDesc(e.target.value)}
                    placeholder="描述这个主题的范围..."
                    rows={3}
                    className="w-full px-4 py-2 bg-white border border-border rounded-lg text-text-primary placeholder:text-text-tertiary focus:ring-2 focus:ring-primary/20 focus:border-primary text-sm"
                    disabled={isCreating}
                  />
                </div>
                {error && (
                  <p className="text-sm text-red-500">{error}</p>
                )}
                <div className="flex gap-2">
                  <button
                    onClick={handleCreate}
                    disabled={isCreating}
                    className="flex-1 py-2 px-4 bg-primary hover:bg-primary/90 disabled:bg-text-tertiary text-white font-medium rounded-lg transition-colors flex items-center justify-center gap-2"
                  >
                    {isCreating ? (
                      <>
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                        创建中...
                      </>
                    ) : (
                      <>
                        <Check size={18} />
                        创建
                      </>
                    )}
                  </button>
                  <button
                    onClick={() => {
                      setShowCreateForm(false);
                      setNewTopicName('');
                      setNewTopicDesc('');
                      setError(null);
                    }}
                    disabled={isCreating}
                    className="flex-1 py-2 px-4 bg-bg hover:bg-bg-tertiary text-text-primary font-medium rounded-lg transition-colors border border-border"
                  >
                    取消
                  </button>
                </div>
              </div>
            </div>
          ) : (
            <button
              onClick={() => setShowCreateForm(true)}
              className="w-full py-3 px-4 bg-primary hover:bg-primary/90 text-white font-medium rounded-lg transition-colors mb-6 flex items-center justify-center gap-2"
            >
              <Plus size={20} />
              新建主题
            </button>
          )}

          {/* Topic List */}
          <div className="space-y-3">
            {localTopics.length === 0 ? (
              <div className="text-center py-8 text-text-tertiary">
                <p className="text-lg mb-2">📭</p>
                <p>还没有保存的主题</p>
                <p className="text-sm mt-1">创建一个吧！</p>
              </div>
            ) : (
              localTopics.map(topic => (
                <div
                  key={topic.id}
                  className="p-4 bg-bg/50 rounded-xl hover:bg-bg transition-colors border border-border/50"
                >
                  <div className="flex justify-between items-start gap-4">
                    <div className="flex-1">
                      <h3 className="font-semibold text-text-primary mb-1">
                        {topic.topic_name}
                      </h3>
                      {topic.description && (
                        <p className="text-sm text-text-secondary">
                          {topic.description}
                        </p>
                      )}
                      <p className="text-xs text-text-tertiary mt-2">
                        创建于 {new Date(topic.created_at).toLocaleDateString('zh-CN')}
                      </p>
                    </div>
                    <div className="flex gap-2">
                      {onSelectTopic && (
                        <button
                          onClick={() => {
                            onSelectTopic(topic);
                            onClose();
                          }}
                          className="py-1 px-3 text-sm bg-primary/10 text-primary rounded-lg hover:bg-primary/20 transition-colors"
                        >
                          选择
                        </button>
                      )}
                      <button
                        onClick={() => handleDelete(topic.id)}
                        className="py-1 px-3 text-sm bg-red-50 dark:bg-red-900/30 text-red-500 rounded-lg hover:bg-red-100 dark:hover:bg-red-900/50 transition-colors"
                      >
                        <Trash2 size={16} />
                      </button>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
