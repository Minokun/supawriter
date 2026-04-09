/**
 * 热点数据 API
 */

import { apiClient } from './client';

// ============ V1 Types (Legacy) ============

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

// ============ V2 Types ============

export interface HotspotItemV2 {
  id: number;
  title: string;
  url?: string;
  source: string;
  rank: number;
  rank_prev?: number;
  rank_change: number;
  hot_value?: number;
  is_new: boolean;
  description?: string;
  updated_at: string;
}

export interface HotspotSourceV2 {
  id: string;
  name: string;
  icon?: string;
  category?: string;
  enabled: boolean;
}

export interface HotspotListResponseV2 {
  source: string;
  updated_at: string;
  items: HotspotItemV2[];
  count: number;
}

export interface SyncResultV2 {
  source: string;
  success: boolean;
  created: number;
  updated: number;
  total: number;
  error?: string;
}

export interface RankHistoryItem {
  rank: number;
  hot_value?: number;
  is_new: boolean;
  recorded_at: string;
}

export class HotspotsApi {
  /**
   * 获取热点数据 (V1 - Legacy)
   */
  async getHotspots(source: string = 'baidu'): Promise<{
    source: string;
    data: HotspotItem[];
    from_cache: boolean;
    count: number;
  }> {
    return apiClient.get(`/api/v1/hotspots/?source=${source}`);
  }

  /**
   * 获取热点源列表 (V1 - Legacy)
   */
  async getSources(): Promise<{ sources: HotspotSource[] }> {
    return apiClient.get('/api/v1/hotspots/sources');
  }

  // ============ V2 API Methods ============

  /**
   * 获取所有平台列表 (V2)
   */
  async getSourcesV2(): Promise<{ sources: HotspotSourceV2[] }> {
    return apiClient.get('/api/v1/hotspots/v2/sources');
  }

  /**
   * 获取所有平台最新热点 (V2)
   */
  async getAllLatestV2(limit: number = 10): Promise<Record<string, HotspotListResponseV2>> {
    return apiClient.get(`/api/v1/hotspots/v2/latest?limit=${limit}`);
  }

  /**
   * 获取指定平台最新热点 (V2)
   */
  async getLatestBySourceV2(
    source: string,
    limit: number = 50
  ): Promise<HotspotListResponseV2> {
    return apiClient.get(`/api/v1/hotspots/v2/latest/${source}?limit=${limit}`);
  }

  /**
   * 获取热点排名趋势 (V2)
   */
  async getTrendV2(
    hotspotId: number,
    hours: number = 24
  ): Promise<{
    hotspot_id: number;
    source: string;
    history: RankHistoryItem[];
  }> {
    return apiClient.get(`/api/v1/hotspots/v2/trend/${hotspotId}?hours=${hours}`);
  }

  /**
   * 获取平台历史热点 (V2)
   */
  async getSourceHistoryV2(
    source: string,
    hours: number = 24,
    limit: number = 100
  ): Promise<{
    source: string;
    hours: number;
    records: Array<{
      id: number;
      hotspot_item_id: number;
      rank: number;
      hot_value?: number;
      is_new: boolean;
      recorded_at: string;
    }>;
    count: number;
  }> {
    return apiClient.get(
      `/api/v1/hotspots/v2/history/${source}?hours=${hours}&limit=${limit}`
    );
  }

  /**
   * 手动同步热点 (V2)
   */
  async syncHotspotsV2(source?: string): Promise<{
    success: boolean;
    results: Record<string, SyncResultV2>;
  }> {
    const url = source
      ? `/api/v1/hotspots/v2/sync?source=${source}`
      : '/api/v1/hotspots/v2/sync';
    return apiClient.post(url);
  }

  /**
   * 初始化平台配置 (V2)
   */
  async initSourcesV2(): Promise<{
    success: boolean;
    created: number;
    message: string;
  }> {
    return apiClient.post('/api/v1/hotspots/v2/init');
  }

  /**
   * 清除缓存 (V2)
   */
  async clearCacheV2(source?: string): Promise<{
    success: boolean;
    message: string;
  }> {
    const url = source
      ? `/api/v1/hotspots/v2/cache?source=${source}`
      : '/api/v1/hotspots/v2/cache';
    return apiClient.delete(url);
  }
}

export const hotspotsApi = new HotspotsApi();
