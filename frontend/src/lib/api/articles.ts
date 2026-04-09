/**
 * 文章生成 API
 */

import { apiClient } from './client';

export interface ArticleGenerateRequest {
  topic: string;
  model_type?: string;
  model_name?: string;
  knowledge_document_ids?: string[];
  custom_style?: string;
  user_idea?: string;
  user_references?: string;
}

export interface ProgressEvent {
  type: 'progress' | 'completed' | 'error';
  article_id: string;
  progress_percent: number;
  current_step: string;
  timestamp: string;
  data?: {
    content?: string;
    outline?: any;
  };
  error_message?: string;
}

export interface ArticleProgress {
  article_id: string;
  status: string;
  progress_percent: number;
  current_step: string;
  error_message?: string;
  content?: string;
  outline?: any;
}

export interface QueueItem {
  article_id: string;
  topic: string;
  status: string;
  created_at: string;
  completed_at?: string;
}

export class ArticlesApi {
  /**
   * 流式生成文章（SSE）
   */
  generateArticleStream(
    request: ArticleGenerateRequest,
    onProgress: (event: ProgressEvent) => void,
    onError?: (error: Error) => void
  ): EventSource {
    return apiClient.createEventSource(
      '/api/v1/articles/generate/stream',
      onProgress,
      onError
    );
  }

  /**
   * 查询文章生成进度
   */
  async getProgress(articleId: string): Promise<ArticleProgress> {
    return apiClient.get(`/api/v1/articles/generate/progress/${articleId}`);
  }

  /**
   * 获取用户队列
   */
  async getQueue(limit: number = 20): Promise<{
    items: QueueItem[];
    total: number;
  }> {
    return apiClient.get(`/api/v1/articles/queue?limit=${limit}`);
  }

  /**
   * 从队列中移除
   */
  async removeFromQueue(articleId: string): Promise<{ message: string }> {
    return apiClient.delete(`/api/v1/articles/queue/${articleId}`);
  }
}

export const articlesApi = new ArticlesApi();
