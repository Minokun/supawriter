'use client';

import { memo, forwardRef } from 'react';
import NovelEditor from '../ui/NovelEditor';

interface EnhancedMarkdownProps {
  content: string;
  className?: string;
  style?: 'wechat' | 'modern' | 'github' | 'zhihu' | 'futuristic' | 'elegant'; 
  codeTheme?: string; 
  showCopyButton?: boolean; 
  enableImagePreview?: boolean; 
  readOnly?: boolean;
}

/**
 * Enhanced Markdown Component (Powered by Novel)
 */
const EnhancedMarkdown = memo(forwardRef<any, EnhancedMarkdownProps>(({
  content,
  className = '',
  style = 'wechat',
  readOnly = true,
}, ref) => {
  const styleClass = `style-${style}`;

  return (
    <div className={`enhanced-markdown-wrapper ${styleClass} ${className}`}>
      <NovelEditor ref={ref} content={content} readOnly={readOnly} />
    </div>
  );
}));

EnhancedMarkdown.displayName = 'EnhancedMarkdown';

export default EnhancedMarkdown;