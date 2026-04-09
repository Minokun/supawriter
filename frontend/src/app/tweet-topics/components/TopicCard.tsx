'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { ChevronDown, ChevronUp, Copy, Sparkles } from 'lucide-react';
import type { TopicDetail } from '@/types/tweet-topics';

interface TopicCardProps {
  topic: TopicDetail;
  index: number;
  newsUrls?: string[]; // 来源新闻链接列表（已废弃，保留用于兼容）
}

export function TopicCard({ topic, index }: TopicCardProps) {
  const router = useRouter();
  // 仅使用当前 topic 的匹配来源链接，避免误将整批新闻链接带入写作页
  const relevantUrls = (topic.source_urls || []).filter(Boolean);
  const primarySourceUrl = relevantUrls[0];
  const [expanded, setExpanded] = useState(false);

  const getHeatColor = (score: number = 5) => {
    if (score >= 8) return 'text-red-500';
    if (score >= 5) return 'text-yellow-500';
    return 'text-gray-500';
  };

  const getFireEmoji = (score: number = 5) => {
    return '🔥'.repeat(Math.min(Math.floor(score / 2), 5));
  };

  const getDifficultyColor = (difficulty?: string) => {
    if (!difficulty) return 'text-gray-500';
    if (difficulty === '简单') return 'text-green-500';
    if (difficulty === '中等') return 'text-yellow-500';
    return 'text-red-500';
  };

  const getDifficultyEmoji = (difficulty?: string) => {
    if (!difficulty) return '⚪';
    if (difficulty === '简单') return '🟢';
    if (difficulty === '中等') return '🟡';
    return '🔴';
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-border/50 overflow-hidden hover:shadow-strong transition-shadow">
      {/* Card Header */}
      <div className="p-6">
        <div className="flex justify-between items-start gap-4">
          {/* Left Content */}
          <div className="flex-1">
            {/* Index and Title */}
            <div className="flex items-center gap-3 mb-2">
              <span className="text-2xl font-bold text-primary">
                #{index}
              </span>
              <h3 className="text-xl font-bold text-text-primary">
                {topic.title}
              </h3>
            </div>

            {/* Subtitle */}
            {topic.subtitle && (
              <p className="text-text-secondary italic mb-4">
                {topic.subtitle}
              </p>
            )}

            {/* Meta Tags */}
            <div className="flex flex-wrap gap-2 mb-3">
              {topic.angle && (
                <span className="inline-flex items-center px-2 py-1 rounded-lg text-xs font-medium bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300">
                  📐 {topic.angle}
                </span>
              )}
              {topic.target_audience && (
                <span className="inline-flex items-center px-2 py-1 rounded-lg text-xs font-medium bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300">
                  👥 {topic.target_audience}
                </span>
              )}
              {topic.difficulty && (
                <span className={`inline-flex items-center px-2 py-1 rounded-lg text-xs font-medium ${getDifficultyColor(topic.difficulty)}`}>
                  {getDifficultyEmoji(topic.difficulty)} {topic.difficulty}
                </span>
              )}
              {topic.estimated_words && (
                <span className="inline-flex items-center px-2 py-1 rounded-lg text-xs font-medium bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300">
                  📏 {topic.estimated_words}
                </span>
              )}
            </div>

            {/* SEO Keywords */}
            {topic.seo_keywords && topic.seo_keywords.length > 0 && (
              <div className="flex flex-wrap gap-1 mb-3">
                {topic.seo_keywords.map(keyword => (
                  <span
                    key={keyword}
                    className="inline-flex items-center px-2 py-0.5 rounded-md text-xs bg-primary/5 text-primary"
                  >
                    {keyword}
                  </span>
                ))}
              </div>
            )}
          </div>

          {/* Heat Score */}
          <div className={`text-2xl font-bold ${getHeatColor(topic.heat_score)}`}>
            {getFireEmoji(topic.heat_score)} {topic.heat_score || 5}/10
          </div>
        </div>

        {/* Source News */}
        {(topic.source_news || topic.source_news_title) && (
          <div className="mt-3 pt-3 border-t border-border">
            <p className="text-xs text-text-tertiary">
              📰 来源：{topic.source_news_title || topic.source_news}
              {relevantUrls && relevantUrls.length > 0 && (
                <span className="ml-2 text-primary">
                  ({relevantUrls.length} 个链接)
                </span>
              )}
            </p>
          </div>
        )}

        {/* Expand Button */}
        <button
          onClick={() => setExpanded(!expanded)}
          className="mt-4 text-sm text-primary hover:text-primary/80 flex items-center gap-1"
        >
          {expanded ? (
            <>收起详情 <ChevronUp size={16} /></>
          ) : (
            <>查看详情 <ChevronDown size={16} /></>
          )}
        </button>
      </div>

      {/* Detailed Content (Expandable) */}
      {expanded && (
        <div className="px-6 pb-6 border-t border-border bg-bg/30">
          {/* Hook */}
          {topic.hook && (
            <div className="mb-4">
              <h4 className="text-sm font-semibold text-text-primary mb-2 flex items-center gap-2">
                🎣 开篇钩子
              </h4>
              <p className="text-sm text-text-secondary bg-green-50 dark:bg-green-900/20 p-3 rounded-lg border border-green-100 dark:border-green-800">
                {topic.hook}
              </p>
            </div>
          )}

          {/* Value Proposition */}
          {topic.value_proposition && (
            <div className="mb-4">
              <h4 className="text-sm font-semibold text-text-primary mb-2 flex items-center gap-2">
                💎 价值主张
              </h4>
              <p className="text-sm text-text-secondary bg-blue-50 dark:bg-blue-900/20 p-3 rounded-lg border border-blue-100 dark:border-blue-800">
                {topic.value_proposition}
              </p>
            </div>
          )}

          {/* Content Outline */}
          {topic.content_outline && topic.content_outline.length > 0 && (
            <div className="mb-4">
              <h4 className="text-sm font-semibold text-text-primary mb-2 flex items-center gap-2">
                📑 内容大纲
              </h4>
              <div className="text-sm text-text-secondary bg-bg p-3 rounded-lg">
                {topic.content_outline.map((section, idx) => {
                  if (typeof section === 'string') {
                    return <p key={idx} className="mb-1">{idx + 1}. {section}</p>;
                  }
                  return (
                    <div key={idx} className="mb-2">
                      <p className="font-medium">{section.h1}</p>
                      {section.h2 && Array.isArray(section.h2) && (
                        <ul className="ml-4 list-disc">
                          {section.h2.map((h2, h2Idx) => (
                            <li key={h2Idx} className="text-xs">{h2}</li>
                          ))}
                        </ul>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Interaction Point and Share Trigger */}
          <div className="grid md:grid-cols-2 gap-4 mb-4">
            {topic.interaction_point && (
              <div>
                <h4 className="text-sm font-semibold text-text-primary mb-2 flex items-center gap-2">
                  💬 互动引导
                </h4>
                <p className="text-sm text-text-secondary">
                  {topic.interaction_point}
                </p>
              </div>
            )}
            {topic.share_trigger && (
              <div>
                <h4 className="text-sm font-semibold text-text-primary mb-2 flex items-center gap-2">
                  🔄 分享触发
                </h4>
                <p className="text-sm text-text-secondary">
                  {topic.share_trigger}
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Action Buttons */}
      <div className="px-6 py-4 bg-bg/50 border-t border-border flex gap-2">
        <button
          onClick={() => copyToClipboard(topic.title)}
          className="flex-1 py-2 px-4 text-sm font-medium text-text-primary bg-white border border-border rounded-lg hover:bg-bg hover:border-primary/30 transition-colors flex items-center justify-center gap-2"
        >
          <Copy size={16} />
          复制标题
        </button>
        <button
          onClick={() => {
            const detailText = `标题：${topic.title}\n${topic.subtitle ? `副标题：${topic.subtitle}\n` : ''}${topic.angle ? `切入角度：${topic.angle}\n` : ''}${topic.hook ? `开篇钩子：${topic.hook}\n` : ''}`;
            copyToClipboard(detailText);
          }}
          className="flex-1 py-2 px-4 text-sm font-medium text-text-primary bg-white border border-border rounded-lg hover:bg-bg hover:border-primary/30 transition-colors flex items-center justify-center gap-2"
        >
          <Copy size={16} />
          复制详情
        </button>
        <button
          onClick={() => {
            const params = new URLSearchParams();
            params.set('topic', topic.title);

            // 组合写作要求
            const requirements: string[] = [];
            if (topic.hook) {
              requirements.push(`开篇钩子：${topic.hook}`);
            }
            if (topic.value_proposition) {
              requirements.push(`价值主张：${topic.value_proposition}`);
            }
            if (topic.content_outline && topic.content_outline.length > 0) {
              const outlineText = topic.content_outline.map((section, idx) => {
                if (typeof section === 'string') {
                  return `${idx + 1}. ${section}`;
                }
                let text = section.h1;
                if (section.h2 && Array.isArray(section.h2)) {
                  text += '\n' + section.h2.map((h2) => `  - ${h2}`).join('\n');
                }
                return text;
              }).join('\n');
              requirements.push(`内容大纲：\n${outlineText}`);
            }
            if (topic.interaction_point) {
              requirements.push(`互动引导：${topic.interaction_point}`);
            }
            if (topic.share_trigger) {
              requirements.push(`分享触发：${topic.share_trigger}`);
            }

            if (requirements.length > 0) {
              params.set('requirements', requirements.join('\n\n'));
            }

            // 仅传当前选题对应的一条来源链接
            if (primarySourceUrl) {
              params.set('urls', primarySourceUrl);
            }

            router.push(`/writer?${params.toString()}`);
          }}
          className="flex-1 py-2 px-4 text-sm font-medium text-white bg-primary hover:bg-primary/90 rounded-lg transition-colors flex items-center justify-center gap-2"
        >
          <Sparkles size={16} />
          生成文章
        </button>
      </div>
    </div>
  );
}
