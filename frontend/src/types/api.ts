/**
 * API 类型定义（临时）
 * 用于前端开发时的类型支持
 */

import { apiGet, apiPost, apiPut, apiDelete } from '@/lib/api-client';
import { getApiBaseUrl } from '@/lib/api-base-url';

// =============================================================================
// Article Generation Types (Super Writer)
// =============================================================================

export interface ArticleGenerateRequest {
  topic: string;
  article_type?: string;
  custom_style?: string;
  spider_num?: number;
  enable_images?: boolean;
  extra_urls?: string[];
  model_type?: string;
  model_name?: string;
  user_idea?: string;
  user_references?: string;
}

export interface ArticleTaskProgress {
  task_id: string;
  user_id?: number;
  topic?: string;
  status: 'queued' | 'running' | 'completed' | 'error' | 'failed';
  progress: number;
  progress_text?: string;
  error?: string;
  error_message?: string;
  created_at: string;
  updated_at: string;
  article_type?: string;
}

export interface ArticleQueueResponse {
  items: ArticleTaskProgress[];
  total: number;
}

// Enhanced ProgressEvent
export interface ArticleProgressEvent {
  task_id: string;
  type: 'progress' | 'search' | 'outline' | 'writing' | 'completed' | 'error' | 'failed' | 'pending';
  progress_percent: number;
  current_step: string;
  timestamp: string;
  status: 'queued' | 'running' | 'completed' | 'error' | 'failed';
  data?: {
    search_results?: SearchResultItem[];
    search_stats?: SearchStats;
    images?: ImageItem[];
    outline?: ArticleOutline;
    live_article?: string;
    chapter_index?: number;
    chapter_total?: number;
    references?: ReferenceItem[];
    article_metadata?: Record<string, any>;
    article?: {
      id: string;
      task_id: string;
      title: string;
      content: string;
      summary: string;
      outline?: ArticleOutline;
    };
    error_message?: string;
  };
}

export interface SearchResultItem {
  title: string;
  url: string;
  snippet: string;
  source?: string;
  body?: string;
}

export interface SearchResult {
  title: string;
  url: string;
  snippet: string;
  source?: string;
  body?: string;
  score?: number;
  images?: string[];
  // 搜索结果列表（支持保留在消息中）
  search_data?: SearchResult[];
}

// 消息接口（添加搜索结果支持）
export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  thinking?: string;
  timestamp: Date;
  // 搜索结果（添加到消息中持久保存）
  search_data?: SearchResult[];
}

export interface SearchStats {
  original_query: string;
  optimized_query: string;
  ddgs_count: number;
  serper_count: number;
  total_before_llm_filter: number;
  total_after_llm_filter: number;
  total_after_dedup: number;
  final_count: number;
  web_images_count: number;
  total_images_count: number;
}

export interface ImageItem {
  url: string;
  title: string;
}

export interface ReferenceItem {
  title: string;
  url: string;
}

export interface ArticleOutline {
  title: string;
  summary: string;
  content_outline: OutlineSection[];
}

export interface OutlineSection {
  h1: string;
  h2: string[];
}

// =============================================================================
// Legacy types (kept for compatibility)
// =============================================================================

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

export interface HotspotItem {
  title: string;
  url?: string;
  desc?: string;
  hot_score?: string;
  hot_value?: number;
  heat?: string;
  hot?: string;
}

export interface HotspotSource {
  id: string;
  name: string;
  icon: string;
}

// 临时的 articlesApi 实现
export const articlesApi = {
  generateArticleStream: (
    request: ArticleGenerateRequest,
    onProgress: (event: ProgressEvent) => void,
    onError?: (error: Error) => void
  ): EventSource => {
    // 临时实现：返回模拟的 EventSource
    const eventSource = new EventSource('/api/v1/articles/generate/stream');
    
    eventSource.onmessage = (event) => {
      if (event.data === '[DONE]') {
        eventSource.close();
        return;
      }

      try {
        const data = JSON.parse(event.data);
        onProgress(data);
      } catch (error) {
        console.error('Failed to parse SSE data:', error);
      }
    };

    eventSource.onerror = () => {
      eventSource.close();
      if (onError) {
        onError(new Error('SSE connection error'));
      }
    };

    return eventSource;
  }
};

// 临时的 hotspotsApi 实现
export interface Article {
  id: string;
  user_id: number;
  title: string;
  slug: string;
  content: string;
  topic?: string;  // 文章主题
  status: 'draft' | 'published' | 'archived';
  created_at: string;
  updated_at: string;
  completed_at?: string;
  published_at?: string;
  html_content?: string;
  cover_image?: string;
  tags?: string[];
  model_type?: string;
  model_name?: string;
  spider_num?: number;
  image_enabled?: boolean;
  metadata?: Record<string, any>;
}

export const hotspotsApi = {
  async getHotspots(source: string = 'baidu'): Promise<{
    source: string;
    data: HotspotItem[];
    from_cache: boolean;
    count: number;
  }> {
    const response = await fetch(`/api/v1/hotspots/?source=${source}`);
    if (!response.ok) {
      throw new Error('Failed to fetch hotspots');
    }
    return response.json();
  },

  async getSources(): Promise<{ sources: HotspotSource[] }> {
    const response = await fetch('/api/v1/hotspots/sources');
    if (!response.ok) {
      throw new Error('Failed to fetch sources');
    }
    return response.json();
  }
};

export interface ApiKey {
  provider: string;
  preview: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ModelConfig {
  provider: string;
  model_name: string;
  temperature?: number;
  max_tokens?: number;
}

export interface UserPreferences {
  editor_theme?: string;
  language?: string;
  auto_save?: boolean;
  notifications_enabled?: boolean;
}

// 文章历史 API
const API_URL = getApiBaseUrl();

async function getApiErrorMessage(response: Response, fallbackMessage: string) {
  try {
    const data = await response.json();

    if (typeof data?.detail === 'string' && data.detail.trim()) {
      return data.detail;
    }

    if (typeof data?.message === 'string' && data.message.trim()) {
      return data.message;
    }
  } catch {
    // Ignore invalid JSON and fall back to the caller-provided message.
  }

  return fallbackMessage;
}

export const historyApi = {
  async getArticles(page: number = 1, limit: number = 20): Promise<{
    items: Article[];
    total: number;
    page: number;
    limit: number;
  }> {
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
    const response = await fetch(`${API_URL}/api/v1/articles/?page=${page}&limit=${limit}`, {
      headers: token ? {
        'Authorization': `Bearer ${token}`
      } : {}
    });
    if (!response.ok) {
      throw new Error('Failed to fetch articles');
    }
    return response.json();
  },

  async getArticle(id: string): Promise<Article> {
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
    const response = await fetch(`${API_URL}/api/v1/articles/detail/${id}`, {
      headers: token ? {
        'Authorization': `Bearer ${token}`
      } : {}
    });
    if (!response.ok) {
      throw new Error('Failed to fetch article');
    }
    return response.json();
  },

  async deleteArticle(id: string): Promise<{ message: string }> {
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
    const response = await fetch(`${API_URL}/api/v1/articles/detail/${id}`, {
      method: 'DELETE',
      headers: token ? {
        'Authorization': `Bearer ${token}`
      } : {}
    });
    if (!response.ok) {
      throw new Error('Failed to delete article');
    }
    return response.json();
  },

  async updateArticle(id: string, content: string, title?: string): Promise<{ message: string; id: string }> {
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
    const body: any = { content };
    if (title) body.title = title;
    const response = await fetch(`${API_URL}/api/v1/articles/detail/${id}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { 'Authorization': `Bearer ${token}` } : {})
      },
      body: JSON.stringify(body)
    });
    if (!response.ok) {
      throw new Error('Failed to update article');
    }
    return response.json();
  },

  async convertWechat(markdown: string, style: string = 'wechat'): Promise<{ html: string }> {
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
    const response = await fetch(`${API_URL}/api/v1/articles/convert/wechat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { 'Authorization': `Bearer ${token}` } : {})
      },
      body: JSON.stringify({ markdown, style })
    });
    if (!response.ok) {
      throw new Error('Failed to convert to WeChat format');
    }
    return response.json();
  },

  async convertPlatform(
    markdown: string,
    platform: PlatformType,
    topic: string = ''
  ): Promise<PlatformConvertResponse> {
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
    const response = await fetch(`${API_URL}/api/v1/articles/convert/platform`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { 'Authorization': `Bearer ${token}` } : {})
      },
      body: JSON.stringify({ markdown, platform, topic })
    });
    if (!response.ok) {
      throw new Error('Failed to convert platform format');
    }
    return response.json();
  },

  // 文章评分 API（F4）
  async getArticleScore(articleId: string): Promise<ArticleScoreResponse> {
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
    const response = await fetch(`${API_URL}/api/v1/articles/score/${articleId}`, {
      method: 'GET',
      headers: token ? { 'Authorization': `Bearer ${token}` } : {}
    });
    if (!response.ok) {
      throw new Error('Failed to get article score');
    }
    return response.json();
  },

  async scoreArticle(articleId: string): Promise<ArticleScoreResponse> {
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
    const response = await fetch(`${API_URL}/api/v1/articles/score/${articleId}`, {
      method: 'POST',
      headers: token ? { 'Authorization': `Bearer ${token}` } : {}
    });
    if (!response.ok) {
      throw new Error('Failed to score article');
    }
    return response.json();
  },

  // 风格分析 API（F5）
  async analyzeStyle(content: string): Promise<StyleAnalysisResponse> {
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
    const response = await fetch(`${API_URL}/api/v1/articles/style/analyze`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { 'Authorization': `Bearer ${token}` } : {})
      },
      body: JSON.stringify({ content })
    });
    if (!response.ok) {
      throw new Error('Failed to analyze writing style');
    }
    return response.json();
  },

  async saveWritingStyle(content: string): Promise<StyleAnalysisResponse> {
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
    const response = await fetch(`${API_URL}/api/v1/articles/style/save`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { 'Authorization': `Bearer ${token}` } : {})
      },
      body: JSON.stringify({ content })
    });
    if (!response.ok) {
      throw new Error('Failed to save writing style');
    }
    return response.json();
  },

  async getCurrentStyle(): Promise<WritingStyleStatus> {
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
    const response = await fetch(`${API_URL}/api/v1/articles/style/current`, {
      method: 'GET',
      headers: token ? { 'Authorization': `Bearer ${token}` } : {}
    });
    if (!response.ok) {
      throw new Error('Failed to get current style');
    }
    return response.json();
  },

  async toggleStyle(isActive: boolean = true): Promise<{ message: string }> {
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
    const response = await fetch(`${API_URL}/api/v1/articles/style/toggle?is_active=${isActive}`, {
      method: 'PUT',
      headers: token ? { 'Authorization': `Bearer ${token}` } : {}
    });
    if (!response.ok) {
      throw new Error('Failed to toggle style');
    }
    return response.json();
  },

  async deleteStyle(): Promise<{ message: string }> {
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
    const response = await fetch(`${API_URL}/api/v1/articles/style/delete`, {
      method: 'DELETE',
      headers: token ? { 'Authorization': `Bearer ${token}` } : {}
    });
    if (!response.ok) {
      throw new Error('Failed to delete style');
    }
    return response.json();
  },

  // 新用户引导 API（F6）
  async getOnboardingStatus(): Promise<OnboardingStatus> {
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
    const response = await fetch(`${API_URL}/api/v1/articles/onboarding/status`, {
      method: 'GET',
      headers: token ? { 'Authorization': `Bearer ${token}` } : {}
    });
    if (!response.ok) {
      throw new Error('Failed to get onboarding status');
    }
    return response.json();
  },

  async completeOnboarding(userRole: UserRole): Promise<{ message: string; user_role: UserRole }> {
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
    const response = await fetch(`${API_URL}/api/v1/articles/onboarding/complete`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { 'Authorization': `Bearer ${token}` } : {})
      },
      body: JSON.stringify({ user_role: userRole })
    });
    if (!response.ok) {
      throw new Error('Failed to complete onboarding');
    }
    return response.json();
  },

  async skipOnboarding(): Promise<{ message: string }> {
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
    const response = await fetch(`${API_URL}/api/v1/articles/onboarding/skip`, {
      method: 'POST',
      headers: token ? { 'Authorization': `Bearer ${token}` } : {}
    });
    if (!response.ok) {
      throw new Error('Failed to skip onboarding');
    }
    return response.json();
  },

  // SEO分析 API（P1 F7）- V2优化版支持article_id缓存
  async analyzeSEO(content: string, title: string = '', articleId?: string): Promise<SEOAnalysisResponse> {
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
    const response = await fetch(`${API_URL}/api/v1/articles/seo/analyze`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { 'Authorization': `Bearer ${token}` } : {})
      },
      body: JSON.stringify({ content, title, article_id: articleId })
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail?.message || 'Failed to analyze SEO');
    }
    return response.json();
  },

  async extractKeywords(content: string, title: string = '', count: number = 5): Promise<{ keywords: KeywordAnalysis[] }> {
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
    const response = await fetch(`${API_URL}/api/v1/articles/seo/keywords`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { 'Authorization': `Bearer ${token}` } : {})
      },
      body: JSON.stringify({ content, title, count })
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail?.message || 'Failed to extract keywords');
    }
    return response.json();
  },

  async optimizeTitle(content: string, currentTitle: string = ''): Promise<TitleOptimization> {
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
    const response = await fetch(`${API_URL}/api/v1/articles/seo/optimize-title`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { 'Authorization': `Bearer ${token}` } : {})
      },
      body: JSON.stringify({ content, current_title: currentTitle })
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail?.message || 'Failed to optimize title');
    }
    return response.json();
  },

  async generateMetaDescription(content: string, title: string = ''): Promise<MetaDescription> {
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
    const response = await fetch(`${API_URL}/api/v1/articles/seo/meta-description`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { 'Authorization': `Bearer ${token}` } : {})
      },
      body: JSON.stringify({ content, title })
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail?.message || 'Failed to generate meta description');
    }
    return response.json();
  },

  async getInternalLinks(content: string, articleId?: string, limit: number = 5): Promise<{ suggestions: InternalLinkSuggestion[] }> {
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
    const response = await fetch(`${API_URL}/api/v1/articles/seo/internal-links`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { 'Authorization': `Bearer ${token}` } : {})
      },
      body: JSON.stringify({ content, article_id: articleId, limit })
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail?.message || 'Failed to get internal links');
    }
    return response.json();
  }
};

// 系统设置 API
export const settingsApi = {
  async getApiKeys(): Promise<{ keys: ApiKey[] }> {
    return apiGet('/api/v1/settings/keys');
  },

  async createApiKey(data: { provider: string; api_key: string; is_active?: boolean }): Promise<ApiKey> {
    return apiPost('/api/v1/settings/keys', data);
  },

  async deleteApiKey(provider: string): Promise<{ message: string }> {
    return apiDelete(`/api/v1/settings/keys/${provider}`);
  },

  async getModelConfig(): Promise<{
    chat_model?: ModelConfig;
    writer_model?: ModelConfig;
    embedding_model?: ModelConfig;
  }> {
    return apiGet('/api/v1/settings/models');
  },

  async updateModelConfig(data: {
    chat_model?: ModelConfig;
    writer_model?: ModelConfig;
    embedding_model?: ModelConfig;
  }): Promise<any> {
    return apiPut('/api/v1/settings/models', data);
  },

  async getPreferences(): Promise<UserPreferences> {
    return apiGet('/api/v1/settings/preferences');
  },

  async updatePreferences(data: UserPreferences): Promise<UserPreferences> {
    return apiPut('/api/v1/settings/preferences', data);
  }
};

// =============================================================================
// Membership Tier Types
// =============================================================================

export type MembershipTier = 'free' | 'pro' | 'ultra' | 'superuser';

export interface TierDefaults {
  tier: MembershipTier;
  default_chat_model?: string;
  default_writer_model?: string;
  article_limit_per_month: number;
  updated_at: string;
}

export interface TierModelConfig {
  name: string;
  min_tier: MembershipTier;
}

export interface TierAvailableModel {
  provider: string;
  model: string;
  min_tier: MembershipTier;
}

export interface AllTierDefaults {
  [key: string]: {
    default_chat_model?: string;
    default_writer_model?: string;
    article_limit_per_month: number;
    updated_at: string;
  };
}

export interface GlobalLLMProvider {
  id: number;
  provider_id: string;
  provider_name: string;
  base_url: string;
  models: TierModelConfig[];  // [{"name": "deepseek-chat", "min_tier": "free"}]
  enabled: boolean;
}

export interface UserSearchResult {
  id: number;
  username: string;
  email: string;
  display_name: string;
  membership_tier: MembershipTier;
  is_superuser: boolean;
  created_at: string;
}

export interface AvailableModelsResponse {
  tier: MembershipTier;
  models: TierAvailableModel[];
}

export interface UserQuotaResponse {
  allowed: boolean;
  used: number;
  limit: number;
  remaining: number;
}

export type PlatformType = 'wechat' | 'zhihu' | 'xiaohongshu' | 'toutiao' | 'csdn' | 'baijiahao' | 'zsxq';

export interface PlatformConvertResponse {
  content: string;
  format: 'html' | 'markdown' | 'text';
  tags: string[];
  word_count: number;
  copy_format: 'rich_text' | 'plain_text';
}


// ================== 文章评分（F4） ==================

export interface ScoreDimension {
  name: string;
  label: string;
  score: number;
  weight: number;
  suggestions: string[];
}

export interface ArticleScoreResponse {
  total_score: number;
  level: 'excellent' | 'good' | 'average' | 'poor';
  summary: string;
  dimensions: ScoreDimension[];
  scored_at: string;
}


// ================== 写作风格（F5） ==================

export interface StyleDimension {
  style: string;
  label: string;
  description: string;
  confidence?: number;
  avg_length?: number;
  richness?: number;
}

export interface StyleProfile {
  tone: StyleDimension;
  sentence_style: StyleDimension;
  vocabulary: StyleDimension;
  paragraph_structure: StyleDimension;
  opening_style: StyleDimension;
  closing_style: StyleDimension;
}

export interface StyleAnalysisResponse {
  style_profile: StyleProfile;
  summary: string;
}

export interface WritingStyleStatus {
  has_style: boolean;
  style_profile: StyleProfile | null;
  sample_filenames: string[];
  sample_count: number;
  is_active: boolean;
}


// ================== 新用户引导（F6） ==================

export type UserRole = 'media_operator' | 'marketer' | 'freelancer' | 'personal_ip';

export interface OnboardingStatus {
  completed: boolean;
  user_role: UserRole | null;
  completed_at: string | null;
}

export const USER_ROLE_LABELS: Record<UserRole, string> = {
  media_operator: '媒体运营',
  marketer: '市场营销',
  freelancer: '自由职业者',
  personal_ip: '个人博主'
};


// ================== SEO分析（P1 F7） ==================

export interface KeywordDensityInfo {
  keyword: string;
  density: number;
  count: number;
  status: 'good' | 'acceptable' | 'low' | 'high';
  color: 'green' | 'yellow' | 'red';
  suggestion: string;
}

export interface KeywordAnalysis {
  keyword: string;
  relevance: number;
  density: KeywordDensityInfo;
}

export interface TitleOptimization {
  score: number;
  current_title: string;
  feedback: string;
  suggestions: Array<{
    title: string;
    reason: string;
  }>;
}

export interface MetaDescription {
  description: string;
  length: number;
  status: 'good' | 'acceptable' | 'needs_improvement' | 'fallback';
  color: 'green' | 'yellow' | 'red' | 'gray';
  suggestion: string;
}

export interface InternalLinkSuggestion {
  article_id: string;
  title: string;
  relevance: number;
  reason: string;
  suggested_anchor_text: string;
}

export interface SEOScoreInfo {
  score: number;
  level: 'excellent' | 'good' | 'average' | 'poor';
  level_label: string;
  color: 'green' | 'blue' | 'yellow' | 'red';
  feedback: string[];
}

export interface SEOAnalysisResponse {
  seo_score: SEOScoreInfo;
  keywords: KeywordAnalysis[];
  title_optimization: TitleOptimization;
  meta_description: MetaDescription;
  internal_links: InternalLinkSuggestion[];
}


// ================== 热点预警 + 数据看板（Sprint 6 F10 + F11） ==================

export interface AlertKeyword {
  id: string;
  keyword: string;
  category?: string;
  is_active: boolean;
  created_at: string;
}

export interface AlertRecord {
  id: string;
  keyword: string;
  hotspot_title: string;
  hotspot_source: string;
  hotspot_url?: string;
  matched_at: string;
  is_read: boolean;
}

export interface NotificationResponse {
  notifications: AlertRecord[];
  total: number;
  unread_count: number;
}

// 基础统计数据 (Free)
export interface DashboardStatsBase {
  total_articles: number;
  total_words: number;
  monthly_articles: number;
  quota_used: number;
  quota_total: number;
}

// Pro 扩展统计
export interface DashboardStatsPro extends DashboardStatsBase {
  avg_score?: number;
  score_history?: { date: string; score: number }[];
  platform_stats?: Record<string, number>;
}

// Ultra 完整统计
export interface DashboardStatsUltra extends DashboardStatsPro {
  hotspot_matches?: number;
  keyword_hit_rate?: number;
  model_usage?: Record<string, number>;
}

export type DashboardStats = DashboardStatsUltra;

// 预警关键词 API
export const alertsApi = {
  async getKeywords(): Promise<{ keywords: AlertKeyword[] }> {
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
    const response = await fetch(`${API_URL}/api/v1/alerts/keywords`, {
      headers: token ? { 'Authorization': `Bearer ${token}` } : {}
    });
    if (!response.ok) throw new Error('Failed to fetch keywords');
    return response.json();
  },

  async addKeyword(keyword: string, category?: string): Promise<AlertKeyword> {
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
    const response = await fetch(`${API_URL}/api/v1/alerts/keywords`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { 'Authorization': `Bearer ${token}` } : {})
      },
      body: JSON.stringify({ keyword, category })
    });
    if (!response.ok) throw new Error('Failed to add keyword');
    return response.json();
  },

  async deleteKeyword(keywordId: string): Promise<{ message: string }> {
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
    const response = await fetch(`${API_URL}/api/v1/alerts/keywords/${keywordId}`, {
      method: 'DELETE',
      headers: token ? { 'Authorization': `Bearer ${token}` } : {}
    });
    if (!response.ok) throw new Error('Failed to delete keyword');
    return response.json();
  },

  async toggleKeyword(keywordId: string, isActive: boolean): Promise<AlertKeyword> {
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
    const response = await fetch(`${API_URL}/api/v1/alerts/keywords/${keywordId}/toggle`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { 'Authorization': `Bearer ${token}` } : {})
      },
      body: JSON.stringify({ is_active: isActive })
    });
    if (!response.ok) throw new Error('Failed to toggle keyword');
    return response.json();
  },

  async suggestKeywords(): Promise<{ keywords: string[] }> {
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
    const response = await fetch(`${API_URL}/api/v1/alerts/suggest-keywords`, {
      headers: token ? { 'Authorization': `Bearer ${token}` } : {}
    });
    if (!response.ok) throw new Error('Failed to get suggested keywords');
    return response.json();
  }
};

// 通知 API
export const notificationsApi = {
  async getNotifications(page: number = 1, limit: number = 20): Promise<NotificationResponse> {
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
    const response = await fetch(`${API_URL}/api/v1/alerts/notifications?page=${page}&limit=${limit}`, {
      headers: token ? { 'Authorization': `Bearer ${token}` } : {}
    });
    if (!response.ok) throw new Error('Failed to fetch notifications');
    return response.json();
  },

  async getUnreadCount(): Promise<{ count: number }> {
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
    const response = await fetch(`${API_URL}/api/v1/alerts/notifications/unread-count`, {
      headers: token ? { 'Authorization': `Bearer ${token}` } : {}
    });
    if (!response.ok) throw new Error('Failed to fetch unread count');
    return response.json();
  },

  async markAsRead(notificationId: string): Promise<AlertRecord> {
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
    const response = await fetch(`${API_URL}/api/v1/alerts/notifications/${notificationId}/read`, {
      method: 'PUT',
      headers: token ? { 'Authorization': `Bearer ${token}` } : {}
    });
    if (!response.ok) throw new Error('Failed to mark as read');
    return response.json();
  },

  async markAllRead(): Promise<{ message: string; count: number }> {
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
    const response = await fetch(`${API_URL}/api/v1/alerts/notifications/read-all`, {
      method: 'PUT',
      headers: token ? { 'Authorization': `Bearer ${token}` } : {}
    });
    if (!response.ok) throw new Error('Failed to mark all as read');
    return response.json();
  },

  async deleteNotification(notificationId: string): Promise<{ message: string }> {
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
    const response = await fetch(`${API_URL}/api/v1/alerts/notifications/${notificationId}`, {
      method: 'DELETE',
      headers: token ? { 'Authorization': `Bearer ${token}` } : {}
    });
    if (!response.ok) throw new Error('Failed to delete notification');
    return response.json();
  }
};

// 数据看板 API
export const dashboardApi = {
  async getStats(): Promise<DashboardStats> {
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
    const response = await fetch(`${API_URL}/api/v1/dashboard`, {
      headers: token ? { 'Authorization': `Bearer ${token}` } : {}
    });
    if (!response.ok) throw new Error('Failed to fetch dashboard stats');
    return response.json();
  }
};

// ================== 批量生成（Sprint 7 F8） ==================

export interface BatchJob {
  id: string;
  name: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'partial';
  total_count: number;
  completed_count: number;
  failed_count: number;
  progress: number;
  zip_url?: string;
  created_at: string;
}

export interface BatchTask {
  id: string;
  topic: string;
  status: string;
  article_id?: string;
  error_message?: string;
}

export interface CreateBatchJobRequest {
  name: string;
  topics: string[];
  platform: string;
  style_id?: string;
  concurrency?: number;
  generate_images?: boolean;
}

// 批量生成 API
export const batchApi = {
  async createJob(data: CreateBatchJobRequest): Promise<BatchJob> {
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
    const response = await fetch(`${API_URL}/api/v1/batch/jobs`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { 'Authorization': `Bearer ${token}` } : {})
      },
      body: JSON.stringify(data)
    });
    if (!response.ok) throw new Error(await getApiErrorMessage(response, '创建批量任务失败'));
    return response.json();
  },

  async getJobs(): Promise<{ jobs: BatchJob[] }> {
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
    const response = await fetch(`${API_URL}/api/v1/batch/jobs`, {
      headers: token ? { 'Authorization': `Bearer ${token}` } : {}
    });
    if (!response.ok) throw new Error(await getApiErrorMessage(response, '加载批量任务失败，请重试'));
    const data = await response.json();
    return { jobs: data.items || data.jobs || [] };
  },

  async getJob(id: string): Promise<{ job: BatchJob; tasks: BatchTask[] }> {
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
    const response = await fetch(`${API_URL}/api/v1/batch/jobs/${id}`, {
      headers: token ? { 'Authorization': `Bearer ${token}` } : {}
    });
    if (!response.ok) throw new Error(await getApiErrorMessage(response, '加载任务详情失败'));
    const data = await response.json();
    return {
      job: data.job || data,
      tasks: data.tasks || data.job?.tasks || [],
    };
  },

  async retryJob(id: string): Promise<{ message: string; retried_count: number }> {
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
    const response = await fetch(`${API_URL}/api/v1/batch/jobs/${id}/retry`, {
      method: 'POST',
      headers: token ? { 'Authorization': `Bearer ${token}` } : {}
    });
    if (!response.ok) throw new Error(await getApiErrorMessage(response, '重试失败'));
    return response.json();
  },

  async cancelJob(id: string): Promise<{ message: string }> {
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
    const response = await fetch(`${API_URL}/api/v1/batch/jobs/${id}/cancel`, {
      method: 'POST',
      headers: token ? { 'Authorization': `Bearer ${token}` } : {}
    });
    if (!response.ok) throw new Error(await getApiErrorMessage(response, '取消任务失败'));
    return response.json();
  },

  async downloadZip(id: string): Promise<Blob> {
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
    const response = await fetch(`${API_URL}/api/v1/batch/jobs/${id}/download`, {
      headers: token ? { 'Authorization': `Bearer ${token}` } : {}
    });
    if (!response.ok) throw new Error(await getApiErrorMessage(response, '下载失败'));
    return response.blob();
  }
};


// ================== 写作Agent（Sprint 7 F9） ==================

export interface WritingAgent {
  id: string;
  name: string;
  is_active: boolean;
  trigger_rules: {
    sources: string[];
    keywords?: string[];
    min_heat?: number;
  };
  platform: string;
  max_daily: number;
  today_triggered: number;
  total_triggered: number;
}

export interface AgentDraft {
  id: string;
  agent_name: string;
  hotspot_title: string;
  hotspot_source: string;
  hotspot_heat?: number;
  status: string;
  article_id?: string;
  created_at: string;
}

export interface CreateAgentRequest {
  name: string;
  trigger_rules: {
    sources: string[];
    keywords?: string[];
    min_heat?: number;
  };
  platform: string;
  style_id?: string;
  max_daily?: number;
}

// 写作Agent API
export const agentApi = {
  async createAgent(data: CreateAgentRequest): Promise<WritingAgent> {
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
    const response = await fetch(`${API_URL}/api/v1/agents`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { 'Authorization': `Bearer ${token}` } : {})
      },
      body: JSON.stringify(data)
    });
    if (!response.ok) throw new Error(await getApiErrorMessage(response, '创建Agent失败'));
    return response.json();
  },

  async getAgents(): Promise<{ agents: WritingAgent[] }> {
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
    const response = await fetch(`${API_URL}/api/v1/agents`, {
      headers: token ? { 'Authorization': `Bearer ${token}` } : {}
    });
    if (!response.ok) throw new Error(await getApiErrorMessage(response, '加载写作 Agent 失败，请重试'));
    return response.json();
  },

  async updateAgent(id: string, data: Partial<WritingAgent>): Promise<WritingAgent> {
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
    const response = await fetch(`${API_URL}/api/v1/agents/${id}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { 'Authorization': `Bearer ${token}` } : {})
      },
      body: JSON.stringify(data)
    });
    if (!response.ok) throw new Error(await getApiErrorMessage(response, '更新Agent失败'));
    return response.json();
  },

  async deleteAgent(id: string): Promise<{ message: string }> {
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
    const response = await fetch(`${API_URL}/api/v1/agents/${id}`, {
      method: 'DELETE',
      headers: token ? { 'Authorization': `Bearer ${token}` } : {}
    });
    if (!response.ok) throw new Error(await getApiErrorMessage(response, '删除失败'));
    return response.json();
  },

  async getDrafts(params?: { status?: string; page?: number; limit?: number }): Promise<{ drafts: AgentDraft[]; total: number; page: number; limit: number; pages: number }> {
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
    const queryParams = new URLSearchParams();
    if (params?.status) queryParams.append('status', params.status);
    queryParams.append('page', String(params?.page ?? 1));
    queryParams.append('limit', String(params?.limit ?? 20));
    const response = await fetch(`${API_URL}/api/v1/agents/drafts?${queryParams}`, {
      headers: token ? { 'Authorization': `Bearer ${token}` } : {}
    });
    if (!response.ok) throw new Error(await getApiErrorMessage(response, '加载草稿失败，请重试'));
    const data = await response.json();
    // 后端返回 {items, total, page, limit, pages}，映射 items -> drafts
    return {
      drafts: data.items || [],
      total: data.total || 0,
      page: data.page || 1,
      limit: data.limit || 20,
      pages: data.pages || 1
    };
  },

  async reviewDraft(id: string, action: 'accept' | 'discard', rating?: number, notes?: string): Promise<{ message: string }> {
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
    const response = await fetch(`${API_URL}/api/v1/agents/drafts/${id}/review`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { 'Authorization': `Bearer ${token}` } : {})
      },
      body: JSON.stringify({ action, rating, notes })
    });
    if (!response.ok) throw new Error(await getApiErrorMessage(response, '操作失败'));
    return response.json();
  }
};
