// 推文选题相关类型定义

export interface UserTopic {
  id: number;
  user_id: number;
  topic_name: string;
  description?: string;
  created_at: string;
  updated_at: string;
}

export interface TopicDetail {
  title: string;
  subtitle?: string;
  angle?: string;
  target_audience?: string;
  seo_keywords?: string[];
  tags?: string[];
  content_outline?: Array<{ h1?: string; h2?: string[] } | string>;
  hook?: string;
  value_proposition?: string;
  interaction_point?: string;
  share_trigger?: string;
  estimated_words?: string;
  difficulty?: string;
  heat_score?: number;
  source_news?: string; // 智能模式：来源新闻
  source_news_title?: string; // 主要来源新闻标题
  source_urls?: string[]; // 该topic相关的来源链接列表
}

export interface FilteredNews {
  title: string;
  relevance_score: number;
  reason: string;
}

export interface TopicsData {
  topics: TopicDetail[];
  summary?: string;
  hot_keywords?: string[];
  filtered_news?: FilteredNews[];
}

export interface TweetTopicsRecord {
  id: number;
  mode: 'intelligent' | 'manual';
  topic_name?: string;
  news_source: string;
  news_count: number;
  topics_data: TopicsData;
  model_type?: string;
  model_name?: string;
  timestamp: string;
  news_urls?: string[]; // 来源新闻链接列表
}

// 智能模式生成请求
export interface IntelligentGenerateRequest {
  topic_id?: number;
  custom_topic?: string;
  save_topic?: boolean;
  topic_description?: string;
  topic_count?: number;
}

// 手动模式生成请求
export interface ManualGenerateRequest {
  news_source: string;
  news_count?: number;
  topic_count?: number;
}

// API 响应类型
export interface GenerateResponse {
  record_id: number;
  mode: 'intelligent' | 'manual';
  topic_name?: string;
  news_source: string;
  news_count: number;
  topics_data: TopicsData;
  model_type?: string;
  model_name?: string;
  news_urls?: string[]; // 来源新闻链接列表
}

export interface HistoryResponse {
  records: TweetTopicsRecord[];
}
