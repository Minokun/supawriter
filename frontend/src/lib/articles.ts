import { getBackendToken } from './api';
import { getApiBaseUrl } from './api-base-url';
import type {
  ArticleGenerateRequest,
  ArticleTaskProgress,
  ArticleQueueResponse,
  ArticleProgressEvent,
  Article
} from '@/types/api';

// Re-export types
export type { ArticleProgressEvent, ArticleGenerateRequest, ArticleTaskProgress, Article };

const API_URL = getApiBaseUrl();

export class ArticleGenerationError extends Error {
  constructor(message: string, public data?: any) {
    super(message);
    this.name = 'ArticleGenerationError';
  }
}

// Generate article
export async function generateArticle(request: ArticleGenerateRequest): Promise<ArticleTaskProgress> {
  console.log('[generateArticle] Starting article generation...');
  
  const token = await getBackendToken();
  console.log('[generateArticle] Token obtained:', token ? `${token.substring(0, 20)}...` : 'null');
  
  if (!token) {
    console.error('[generateArticle] No token available');
    throw new Error('Not authenticated');
  }

  console.log('[generateArticle] Sending request to:', `${API_URL}/api/v1/articles/generate`);
  
  const response = await fetch(`${API_URL}/api/v1/articles/generate`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify(request),
  });

  console.log('[generateArticle] Response status:', response.status);

  if (!response.ok) {
    const error = await response.json();
    console.error('[generateArticle] Error response:', error);
    throw new ArticleGenerationError(error.detail || 'Failed to create task', error);
  }

  return response.json();
}

// Get task queue
export async function getArticleQueue(): Promise<ArticleQueueResponse> {
  const token = await getBackendToken();
  if (!token) {
    throw new Error('Not authenticated');
  }

  const response = await fetch(`${API_URL}/api/v1/articles/queue`, {
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    throw new Error('Failed to fetch queue');
  }

  return response.json();
}

// Clear entire queue
export async function clearArticleQueue(): Promise<{ message: string; cleared: number }> {
  const token = await getBackendToken();
  if (!token) {
    throw new Error('Not authenticated');
  }

  const response = await fetch(`${API_URL}/api/v1/articles/queue`, {
    method: 'DELETE',
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    throw new Error('Failed to clear queue');
  }

  return response.json();
}

// Remove single task from queue
export async function removeFromQueue(taskId: string): Promise<void> {
  const token = await getBackendToken();
  if (!token) {
    throw new Error('Not authenticated');
  }

  const response = await fetch(`${API_URL}/api/v1/articles/queue/${taskId}`, {
    method: 'DELETE',
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    throw new Error('Failed to remove task from queue');
  }
}

// Stream article progress via SSE
export function streamArticleProgress(
  taskId: string,
  onProgress: (event: ArticleProgressEvent) => void,
  onError?: (error: Error) => void,
  onComplete?: () => void
): () => void {
  let abortController: AbortController | null = null;

  const connect = async () => {
    try {
      const token = await getBackendToken();
      if (!token) {
        throw new Error('Not authenticated');
      }

      abortController = new AbortController();
      const url = `${API_URL}/api/v1/articles/generate/stream/${taskId}`;
      
      const response = await fetch(url, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
        signal: abortController.signal,
        cache: 'no-store',
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('Response body is null');
      }

      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();

        if (done) {
          onComplete?.();
          break;
        }

        buffer += decoder.decode(value, { stream: true });

        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6).trim();
            
            if (data === '[DONE]') {
              onComplete?.();
              return;
            }

            if (data) {
              try {
                const event = JSON.parse(data) as ArticleProgressEvent;
                onProgress(event);
              } catch (error) {
                console.error('Failed to parse SSE data:', error);
              }
            }
          }
        }
      }
    } catch (error) {
      if (error instanceof Error && error.name === 'AbortError') {
        console.log('Stream aborted');
        return;
      }
      console.error('Stream error:', error);
      onError?.(error as Error);
    }
  };

  connect();

  // Return cleanup function
  return () => {
    abortController?.abort();
  };
}

// Save article content
export async function saveArticle(articleId: string, content: string): Promise<Article> {
  const token = await getBackendToken();
  if (!token) {
    throw new Error('Not authenticated');
  }

  const response = await fetch(`${API_URL}/api/v1/articles/${articleId}/save`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify({ content }),
  });

  if (!response.ok) {
    throw new Error('Failed to save article');
  }

  return response.json();
}

// Get article by ID
export async function getArticle(articleId: string): Promise<Article> {
  const token = await getBackendToken();
  if (!token) {
    throw new Error('Not authenticated');
  }

  const response = await fetch(`${API_URL}/api/v1/articles/${articleId}`, {
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    throw new Error('Failed to fetch article');
  }

  return response.json();
}
