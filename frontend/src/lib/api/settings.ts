/**
 * 系统设置 API
 */

import { apiClient } from './client';

export interface ModelConfig {
  provider: string;
  model_name: string;
  temperature?: number;
  max_tokens?: number;
  top_p?: number;
}

export interface UserPreferences {
  editor_theme?: string;
  language?: string;
  auto_save?: boolean;
  notifications_enabled?: boolean;
  default_article_type?: string;
}

export class SettingsApi {
  /**
   * 获取模型配置
   */
  async getModelConfig(): Promise<{
    chat_model?: ModelConfig;
    writer_model?: ModelConfig;
    embedding_model?: ModelConfig;
    image_model?: ModelConfig;
  }> {
    return apiClient.get('/api/v1/settings/models');
  }

  /**
   * 更新模型配置
   */
  async updateModelConfig(data: {
    chat_model?: ModelConfig;
    writer_model?: ModelConfig;
    embedding_model?: ModelConfig;
    image_model?: ModelConfig;
  }): Promise<any> {
    return apiClient.put('/api/v1/settings/models', data);
  }

  /**
   * 获取用户偏好
   */
  async getPreferences(): Promise<UserPreferences> {
    return apiClient.get('/api/v1/settings/preferences');
  }

  /**
   * 更新用户偏好
   */
  async updatePreferences(data: UserPreferences): Promise<UserPreferences> {
    return apiClient.put('/api/v1/settings/preferences', data);
  }
}

export const settingsApi = new SettingsApi();
