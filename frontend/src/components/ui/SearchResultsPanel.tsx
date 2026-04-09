'use client';

import { useState } from 'react';
import { ExternalLink, Search, X, ChevronDown, ChevronUp, Globe, Clock } from 'lucide-react';
import type { SearchResult } from '@/lib/api';

interface SearchResultsPanelProps {
  results: SearchResult[];
  query: string;
  stats?: {
    original_query?: string;
    optimized_query?: string;
    total_count?: number;
  };
  onClose?: () => void;
  loading?: boolean;
}

const SearchResultItem = ({ result }: { result: SearchResult }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <div className="bg-white border border-border rounded-xl p-4 mb-3 hover:border-primary/30 hover:shadow-md transition-all duration-200">
      <a
        href={result.url}
        target="_blank"
        rel="noopener noreferrer"
        className="flex items-start gap-3 group"
      >
        <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0 mt-0.5">
          <Globe size={16} className="text-primary" />
        </div>
        <div className="flex-1 min-w-0">
          <h4 className="font-body text-sm font-bold text-text-primary mb-1 group-hover:text-primary transition-colors line-clamp-2 leading-snug">
            {result.title}
          </h4>
          <div className="flex items-center gap-2 mb-2">
            <span className="text-[10px] text-text-secondary font-medium truncate flex items-center gap-1">
              <ExternalLink size={10} />
              {(() => { try { return new URL(result.url).hostname; } catch { return result.url || '未知来源'; } })()}
            </span>
            {result.score !== undefined && (
              <span className="text-[10px] bg-primary/10 text-primary px-1.5 py-0.5 rounded font-bold">
                {(result.score * 100).toFixed(0)}%
              </span>
            )}
          </div>
          <p className="text-xs text-text-secondary leading-relaxed line-clamp-3">
            {result.snippet || result.body}
          </p>
        </div>
      </a>

      {/* Expandable content for additional details */}
      {(result.body && result.body.length > 200) && (
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="w-full mt-3 flex items-center justify-center gap-1.5 text-[11px] font-bold text-primary hover:text-[#B91C1C] transition-colors"
        >
          {isExpanded ? (
            <>
              <ChevronUp size={12} />
              收起
            </>
          ) : (
            <>
              <ChevronDown size={12} />
              展开更多
            </>
          )}
        </button>
      )}
    </div>
  );
};

export default function SearchResultsPanel({
  results,
  query,
  stats,
  onClose,
  loading = false,
}: SearchResultsPanelProps) {
  const [isCollapsed, setIsCollapsed] = useState(false);

  if (loading) {
    return (
      <div className="bg-white border border-border rounded-2xl p-6 shadow-standard">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-primary/10 rounded-xl flex items-center justify-center">
              <Search size={18} className="text-primary animate-pulse" />
            </div>
            <div>
              <h3 className="font-heading text-base font-bold text-text-primary">
                正在搜索网络...
              </h3>
              <p className="text-xs text-text-secondary font-medium">
                &quot;{query}&quot;
              </p>
            </div>
          </div>
          {onClose && (
            <button
              onClick={onClose}
              className="p-2 rounded-lg hover:bg-bg text-text-secondary hover:text-text-primary transition-colors"
            >
              <X size={16} />
            </button>
          )}
        </div>
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 bg-primary/60 rounded-full animate-bounce" />
          <div className="w-2 h-2 bg-primary/60 rounded-full animate-bounce [animation-delay:0.1s]" />
          <div className="w-2 h-2 bg-primary/60 rounded-full animate-bounce [animation-delay:0.2s]" />
        </div>
      </div>
    );
  }

  if (results.length === 0) {
    return null;
  }

  return (
    <div className="bg-white border border-border rounded-2xl shadow-standard overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-border/50">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-primary/10 rounded-xl flex items-center justify-center">
            <Search size={18} className="text-primary" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="font-heading text-base font-bold text-text-primary">
                搜索结果
              </h3>
              <span className="text-xs bg-primary/10 text-primary px-2 py-0.5 rounded-full font-bold">
                {results.length}
              </span>
            </div>
            <p className="text-xs text-text-secondary font-medium truncate max-w-xs">
              {stats?.optimized_query || query}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-1">
          <button
            onClick={() => setIsCollapsed(!isCollapsed)}
            className="p-2 rounded-lg hover:bg-bg text-text-secondary hover:text-text-primary transition-colors"
            title={isCollapsed ? '展开' : '收起'}
          >
            {isCollapsed ? <ChevronDown size={16} /> : <ChevronUp size={16} />}
          </button>
          {onClose && (
            <button
              onClick={onClose}
              className="p-2 rounded-lg hover:bg-bg text-text-secondary hover:text-text-primary transition-colors"
              title="关闭"
            >
              <X size={16} />
            </button>
          )}
        </div>
      </div>

      {/* Search Stats (if available) */}
      {!isCollapsed && stats && (
        <div className="px-4 py-3 bg-bg/50 border-b border-border/50">
          <div className="flex items-center gap-4 text-xs text-text-secondary">
            <div className="flex items-center gap-1.5">
              <Clock size={12} className="text-text-secondary" />
              <span className="font-medium">优化查询: </span>
              <span className="font-mono bg-white px-1.5 py-0.5 rounded border border-border">
                {stats.optimized_query}
              </span>
            </div>
            {stats.total_count !== undefined && (
              <span className="font-medium">
                找到 {stats.total_count} 条结果
              </span>
            )}
          </div>
        </div>
      )}

      {/* Results List */}
      {!isCollapsed && (
        <div className="p-4 max-h-[400px] overflow-y-auto custom-scrollbar">
          {results.map((result, index) => (
            <SearchResultItem key={`${result.url}-${index}`} result={result} />
          ))}
        </div>
      )}
    </div>
  );
}
