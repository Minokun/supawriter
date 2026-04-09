'use client';

import { memo } from 'react';
import NovelEditor from './NovelEditor';

interface MarkdownContentProps {
  content: string;
  className?: string;
  codeTheme?: string; // Kept for compatibility but unused
  showCopyButton?: boolean; // Kept for compatibility but unused
  enableImagePreview?: boolean; // Kept for compatibility but unused
}

/**
 * Enhanced Markdown 渲染组件 (Powered by Novel)
 */
const MarkdownContent = memo(({
  content,
  className = '',
}: MarkdownContentProps) => {
  return (
    <div className={`markdown-content-wrapper ${className}`}>
      <NovelEditor content={content} readOnly={true} />
    </div>
  );
});

MarkdownContent.displayName = 'MarkdownContent';

export default MarkdownContent;