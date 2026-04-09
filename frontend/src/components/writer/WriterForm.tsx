'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { TextArea } from '@/components/ui/TextArea';
import { Checkbox } from '@/components/ui/Checkbox';
import { generateArticle, type ArticleGenerateRequest } from '@/lib/articles';
import { Loader2, ChevronDown, ChevronUp } from 'lucide-react';
import { CapabilityGate } from '@/components/system/CapabilityGate';
import { useCapabilityReadiness } from '@/lib/capability-readiness';

interface WriterFormProps {
  onSubmit?: (taskId: string) => void;
  disabled?: boolean;
  initialTopic?: string;
  initialCustomStyle?: string;
  initialExtraUrls?: string;
  initialSource?: string;
}

export function WriterForm({ onSubmit, disabled, initialTopic, initialCustomStyle, initialExtraUrls, initialSource }: WriterFormProps) {
  const readiness = useCapabilityReadiness('writer');
  const [topic, setTopic] = useState(initialTopic || '');
  const [userIdea, setUserIdea] = useState('');
  const [userReferences, setUserReferences] = useState('');
  const [customStyle, setCustomStyle] = useState(initialCustomStyle || '');
  const [extraUrls, setExtraUrls] = useState(initialExtraUrls || '');
  const [enableImages, setEnableImages] = useState(true);
  const [enableExtraUrls, setEnableExtraUrls] = useState(!!initialExtraUrls);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [showUserIdea, setShowUserIdea] = useState(false);
  const [showReferences, setShowReferences] = useState(false);
  const [showCustomStyle, setShowCustomStyle] = useState(false);

  useEffect(() => {
    if (initialTopic) {
      setTopic(initialTopic);
    }
    if (initialCustomStyle) {
      setCustomStyle(initialCustomStyle);
      setShowCustomStyle(true);
    }
    if (initialExtraUrls) {
      setExtraUrls(initialExtraUrls);
      setEnableExtraUrls(true);
    }
  }, [initialTopic, initialCustomStyle, initialExtraUrls]);

  useEffect(() => {
    if (initialSource === 'hotspot' && initialTopic) {
      window.requestAnimationFrame(() => {
        const submitButton = document.querySelector<HTMLButtonElement>('[data-testid="writer-submit-button"]');
        submitButton?.focus();
      });
    }
  }, [initialSource, initialTopic]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!topic.trim()) {
      setError('请输入文章主题');
      return;
    }

    setIsSubmitting(true);
    setError('');

    try {
      const request: ArticleGenerateRequest = {
        topic: topic.trim(),
        custom_style: customStyle.trim() || undefined,
        enable_images: enableImages,
        extra_urls: enableExtraUrls
          ? extraUrls.split('\n').map(url => url.trim()).filter(url => url)
          : undefined,
        user_idea: userIdea.trim() || undefined,
        user_references: userReferences.trim() || undefined,
      };

      const result = await generateArticle(request);
      onSubmit?.(result.task_id);

      // Reset form
      setTopic('');
      setUserIdea('');
      setUserReferences('');
      setCustomStyle('');
      setExtraUrls('');
    } catch (err) {
      setError(err instanceof Error ? err.message : '提交失败');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-6" data-testid="writer-form">
      <div>
        <h3 className="font-heading text-lg font-semibold text-text-primary mb-4">
          📝 新建任务
        </h3>

        <form onSubmit={handleSubmit} className="space-y-4">
          <Input
            label="文章主题"
            placeholder="输入你想写的主题，例如：人工智能的发展趋势"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            disabled={disabled || isSubmitting}
            required
            data-testid="topic-input"
          />

          {initialSource === 'hotspot' && (
            <div className="inline-flex items-center px-2 py-1 rounded-md bg-primary/10 text-primary text-xs font-medium">
              📌 来自热点追踪
            </div>
          )}

          {/* 你的想法/观点 - 折叠 */}
          <div className="border border-border rounded-lg overflow-hidden">
            <button
              type="button"
              className="w-full flex items-center justify-between px-4 py-2.5 bg-bg-secondary hover:bg-bg-tertiary transition-colors text-sm text-text-secondary"
              onClick={() => setShowUserIdea(!showUserIdea)}
            >
              <span>你的想法/观点（可选）</span>
              {showUserIdea ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
            </button>
            {showUserIdea && (
              <div className="p-4">
                <TextArea
                  placeholder="输入你对这个主题的观点或角度，例如：我认为 AI 不会取代老师，但会改变教学方式"
                  value={userIdea}
                  onChange={(e) => setUserIdea(e.target.value)}
                  disabled={disabled || isSubmitting}
                  rows={2}
                  data-testid="user-idea-input"
                />
              </div>
            )}
          </div>

          {/* 参考资料 - 折叠 */}
          <div className="border border-border rounded-lg overflow-hidden">
            <button
              type="button"
              className="w-full flex items-center justify-between px-4 py-2.5 bg-bg-secondary hover:bg-bg-tertiary transition-colors text-sm text-text-secondary"
              onClick={() => setShowReferences(!showReferences)}
            >
              <span>参考资料（可选）</span>
              {showReferences ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
            </button>
            {showReferences && (
              <div className="p-4">
                <TextArea
                  placeholder="粘贴参考资料文字，系统会结合你的资料和搜索内容生成文章"
                  value={userReferences}
                  onChange={(e) => setUserReferences(e.target.value)}
                  disabled={disabled || isSubmitting}
                  rows={3}
                  data-testid="user-references-input"
                />
              </div>
            )}
          </div>

          {/* 其它写作要求 - 折叠 */}
          <div className="border border-border rounded-lg overflow-hidden">
            <button
              type="button"
              className="w-full flex items-center justify-between px-4 py-2.5 bg-bg-secondary hover:bg-bg-tertiary transition-colors text-sm text-text-secondary"
              onClick={() => setShowCustomStyle(!showCustomStyle)}
            >
              <span>其它写作要求（可选）</span>
              {showCustomStyle ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
            </button>
            {showCustomStyle && (
              <div className="p-4">
                <TextArea
                  placeholder="例如：专业风格、幽默风趣、学术严谨等"
                  value={customStyle}
                  onChange={(e) => setCustomStyle(e.target.value)}
                  disabled={disabled || isSubmitting}
                  rows={3}
                />
              </div>
            )}
          </div>

          <Checkbox
            label="启用图片插入"
            checked={enableImages}
            onChange={(checked) => setEnableImages(checked)}
            disabled={disabled || isSubmitting}
          />

          <Checkbox
            label="添加额外网页链接"
            checked={enableExtraUrls}
            onChange={(checked) => setEnableExtraUrls(checked)}
            disabled={disabled || isSubmitting}
          />

          {enableExtraUrls && (
            <TextArea
              label="额外网页链接（每行一个）"
              placeholder="https://example.com/article1&#10;https://example.com/article2"
              value={extraUrls}
              onChange={(e) => setExtraUrls(e.target.value)}
              disabled={disabled || isSubmitting}
              rows={4}
            />
          )}

          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
              {error}
            </div>
          )}

          {!readiness.ready && !readiness.loading && (
            <CapabilityGate
              title={readiness.title}
              description={readiness.description}
              ctaHref={readiness.ctaHref}
              ctaLabel={readiness.ctaLabel}
            />
          )}

          <Button
            type="submit"
            variant="primary"
            size="lg"
            className="w-full"
            disabled={disabled || isSubmitting || !topic.trim() || !readiness.ready}
            icon={isSubmitting ? <Loader2 className="animate-spin" size={20} /> : "🚀"}
            data-testid="writer-submit-button"
          >
            {isSubmitting ? '提交中...' : '开始创作'}
          </Button>
        </form>
      </div>
    </div>
  );
}
