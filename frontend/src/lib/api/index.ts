/**
 * SupaWriter API SDK
 * 统一导出所有 API 模块
 */

export { apiClient, type ApiConfig, type ApiError } from './client';
export { settingsApi, type ModelConfig, type UserPreferences } from './settings';
export { articlesApi, type ArticleGenerateRequest, type ProgressEvent, type ArticleProgress } from './articles';
export { hotspotsApi, type HotspotItem, type HotspotSource } from './hotspots';

// 使用示例：
// import { apiClient, settingsApi, articlesApi, hotspotsApi } from '@/lib/api';
