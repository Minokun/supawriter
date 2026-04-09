'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';
import MainLayout from '@/components/layout/MainLayout';
import Card from '@/components/ui/Card';
import Button from '@/components/ui/Button';
import Badge from '@/components/ui/Badge';
import { Eye, EyeOff, Loader2, Check, Plus, Trash2, X } from 'lucide-react';
import { PreferencesSettings } from '@/components/settings/PreferencesSettings';
import { SettingsStateCard } from '@/components/settings/SettingsStateCard';
import { SettingsTabs, type SettingsTab } from '@/components/settings/SettingsTabs';
import { StyleLearning } from '@/components/settings/StyleLearning';
import { SubscriptionManagement } from '@/components/settings/SubscriptionManagement';
import { isAdminOnlySettingsTab, resolveAccessibleSettingsTab } from '@/components/settings/admin-tab-access';
import { buildLlmProvidersSavePayload, mergeProviderModelEdits } from '@/components/settings/llm-provider-save';
import { getSettingsResponseError } from '@/components/settings/settings-response';
import { useToast } from '@/components/ui/ToastContainer';
import Modal from '@/components/ui/Modal';
import { getApiBaseUrl } from '@/lib/api-base-url';
import { clearBackendAuth } from '@/lib/backend-auth-storage';

// 类型定义

interface ModelConfig {
  provider: string;
  model_name: string;
  temperature?: number;
  max_tokens?: number;
}

interface UserPreferences {
  editor_theme?: string;
  language?: string;
  auto_save?: boolean;
  notifications_enabled?: boolean;
}

// LLM 提供商模板接口
interface LLMProviderTemplate {
  id: string;
  name: string;
  base_url: string;
  default_models: string[];
  category: string;
  description: string;
  requires_api_key: boolean;
}

// LLM 提供商配置接口
interface LLMModel {
  name: string;
  min_tier: string;
}

interface LLMProvider {
  id: string;
  name: string;
  models: LLMModel[];
  base_url: string;
  api_key: string;
  enabled: boolean;
}

export default function SettingsPage() {
  const apiUrl = getApiBaseUrl();
  const { status, getAuthHeaders, isAuthenticated, isAdmin } = useAuth();
  const router = useRouter();
  const signInHref = '/auth/signin?callbackUrl=%2Fsettings';
  const [mounted, setMounted] = useState(false);

  const [activeTab, setActiveTab] = useState<SettingsTab>('models');
  const [loading, setLoading] = useState(true);
  const [pageError, setPageError] = useState<string | null>(null);
  
  
  // LLM 提供商配置
  const [availableProviders, setAvailableProviders] = useState<LLMProviderTemplate[]>([]);
  const [llmProviders, setLlmProviders] = useState<LLMProvider[]>([]);
  const [showAddProviderModal, setShowAddProviderModal] = useState(false);
  const [editingProviderModels, setEditingProviderModels] = useState<Record<string, LLMModel[]>>({});
  const [showProviderKeys, setShowProviderKeys] = useState<Record<string, boolean>>({});
  
  // Toast and Modal
  const { showSuccess, showError } = useToast();
  const [modalState, setModalState] = useState<{
    isOpen: boolean;
    title: string;
    message: string;
    onConfirm?: () => void;
    type: 'confirm' | 'alert';
  }>({ isOpen: false, title: '', message: '', type: 'alert' });

  // 其他服务配置
  const [qiniuConfig, setQiniuConfig] = useState({
    domain: '',
    folder: 'supawriter/',
    bucket: '',
    accessKey: '',
    secretKey: '',
    region: 'z2',
    keySet: false
  });

  const [serperApiKey, setSerperApiKey] = useState('');
  const [serperKeySet, setSerperKeySet] = useState(false);

  // 嵌入向量配置
  const [embeddingConfig, setEmbeddingConfig] = useState({
    model: 'Qwen3-VL-Embedding-8B',
    provider: 'gitee',
    dimension: '4096',
    gitee_base_url: 'https://ai.gitee.com/v1',
    gitee_api_key: '',
    key_set: false,
  });
  const [showEmbeddingKey, setShowEmbeddingKey] = useState(false);

  // 保存状态管理
  const [saveStatus, setSaveStatus] = useState<{
    llm: 'idle' | 'success';
    qiniu: 'idle' | 'success';
    serper: 'idle' | 'success';
    models: 'idle' | 'success';
    preferences: 'idle' | 'success';
    embedding: 'idle' | 'success';
  }>({
    llm: 'idle',
    qiniu: 'idle',
    serper: 'idle',
    models: 'idle',
    preferences: 'idle',
    embedding: 'idle',
  });
  
  // 模型配置
  const [chatModel, setChatModel] = useState<ModelConfig>({ provider: 'openai', model_name: 'gpt-4' });
  const [writerModel, setWriterModel] = useState<ModelConfig>({ provider: 'deepseek', model_name: 'deepseek-chat' });
  
  // 用户偏好
  const [preferences, setPreferences] = useState<UserPreferences>({
    editor_theme: 'light',
    language: 'zh-CN',
    auto_save: true,
    notifications_enabled: true
  });

  const handleAuthExpired = useCallback(() => {
    clearBackendAuth();
    showError('登录已失效，请重新登录');
    if (typeof window !== 'undefined') {
      window.setTimeout(() => {
        window.location.replace(signInHref);
      }, 0);
      return;
    }
    router.replace(signInHref);
  }, [router, showError, signInHref]);

  // 初始化检查
  useEffect(() => {
    setMounted(true);
  }, []);

  // getAuthHeaders is provided by useAuth hook

  const loadSettings = useCallback(async (tab: SettingsTab) => {
    if (!isAuthenticated) {
      setLoading(false);
      return;
    }

    if (!isAdmin && isAdminOnlySettingsTab(tab)) {
      setPageError(null);
      setLoading(false);
      return;
    }

    setLoading(true);
    setPageError(null);
    try {
      // 首次加载时获取可用提供商模板
      if (availableProviders.length === 0) {
        try {
          const templatesRes = await fetch(`${apiUrl}/api/v1/settings/llm-provider-templates`);
          if (templatesRes.ok) {
            const templatesData = await templatesRes.json();
            if (templatesData?.templates) {
              setAvailableProviders(templatesData.templates);
            }
          }
        } catch (e) {
          console.error('Failed to load provider templates:', e);
        }
      }

      // 加载 LLM 提供商数据（models 和 llm tab 都需要）
      if (tab === 'models' || tab === 'llm') {
        try {
          // 非管理员用户使用 available-providers 端点，管理员使用 llm-providers 端点
          const providersEndpoint = isAdmin
            ? `${apiUrl}/api/v1/settings/llm-providers`
            : `${apiUrl}/api/v1/settings/available-providers`;

          const providersRes = await fetch(providersEndpoint, {
            headers: await getAuthHeaders()
          });
          if (providersRes.ok) {
            const providersData = await providersRes.json();
            if (providersData?.providers && Array.isArray(providersData.providers)) {
              setLlmProviders(providersData.providers);
            }
          } else if (providersRes.status === 403) {
            // 403 表示非管理员访问了管理员端点，应该使用 available-providers
            console.log('Access denied to admin endpoint, using available-providers');
            const fallbackRes = await fetch(`${apiUrl}/api/v1/settings/available-providers`, {
              headers: await getAuthHeaders()
            });
            if (fallbackRes.ok) {
              const fallbackData = await fallbackRes.json();
              if (fallbackData?.providers && Array.isArray(fallbackData.providers)) {
                setLlmProviders(fallbackData.providers);
              }
            }
          } else if (providersRes.status === 401) {
            handleAuthExpired();
            return;
          } else {
            throw new Error(await getSettingsResponseError(providersRes, '设置加载失败，请检查网络连接后重试。'));
          }
        } catch (e) {
          console.error('Failed to load LLM providers:', e);
          throw e;
        }
      }

      if (tab === 'models') {
        const response = await fetch(`${apiUrl}/api/v1/settings/models`, {
          headers: await getAuthHeaders()
        });
        if (response.ok) {
          const config = await response.json();
          // 解析模型配置字符串 "provider:model_name"
          if (config?.chat_model) {
            const [provider, model_name] = config.chat_model.split(':');
            setChatModel({ provider, model_name });
          }
          if (config?.writer_model) {
            const [provider, model_name] = config.writer_model.split(':');
            setWriterModel({ provider, model_name });
          }
        } else if (response.status === 401) {
          handleAuthExpired();
          return;
        } else {
          throw new Error(await getSettingsResponseError(response, '设置加载失败，请检查网络连接后重试。'));
        }
      } else if (tab === 'llm') {
        // llmProviders 已在上面加载
      } else if (tab === 'services') {
        const response = await fetch(`${apiUrl}/api/v1/settings/services`, {
          headers: await getAuthHeaders()
        });
        if (response.ok) {
          const data = await response.json();
          if (data) {
            setQiniuConfig({
              domain: data.qiniu_domain || '',
              folder: data.qiniu_folder || 'supawriter/',
              bucket: data.qiniu_bucket || '',
              accessKey: data.qiniu_access_key || '',
              secretKey: data.qiniu_secret_key || '',
              region: data.qiniu_region || 'z2',
              keySet: data.qiniu_key_set || false
            });
            setSerperApiKey(data.serper_api_key || '');
            setSerperKeySet(data.serper_key_set || false);

            // 嵌入向量配置
            if (data.embedding_model || data.embedding_gitee_base_url || data.embedding_key_set) {
              setEmbeddingConfig({
                model: data.embedding_model || 'Qwen3-VL-Embedding-8B',
                provider: data.embedding_provider || 'gitee',
                dimension: data.embedding_dimension || '4096',
                gitee_base_url: data.embedding_gitee_base_url || 'https://ai.gitee.com/v1',
                gitee_api_key: data.embedding_gitee_api_key || '',
                key_set: data.embedding_key_set || false,
              });
            }
          }
        } else if (response.status === 401) {
          handleAuthExpired();
          return;
        } else {
          throw new Error(await getSettingsResponseError(response, '设置加载失败，请检查网络连接后重试。'));
        }
      } else if (tab === 'preferences') {
        const response = await fetch(`${apiUrl}/api/v1/settings/preferences`, {
          headers: await getAuthHeaders()
        });
        if (response.ok) {
          const prefs = await response.json();
          if (prefs) setPreferences(prefs);
        } else if (response.status === 401) {
          handleAuthExpired();
          return;
        } else {
          throw new Error(await getSettingsResponseError(response, '设置加载失败，请检查网络连接后重试。'));
        }
      }
    } catch (error) {
      console.error('加载设置失败:', error);
      setPageError(error instanceof Error ? error.message : '设置加载失败，请检查网络连接后重试。');
    } finally {
      setLoading(false);
    }
  }, [isAuthenticated, status, apiUrl, getAuthHeaders, handleAuthExpired, availableProviders.length, isAdmin]);

  useEffect(() => {
    if (mounted && isAuthenticated) {
      loadSettings(activeTab);
    } else if (mounted && status === 'unauthenticated') {
      setLoading(false);
    }
  }, [mounted, status, activeTab, loadSettings]);

  useEffect(() => {
    const nextTab = resolveAccessibleSettingsTab(activeTab, isAdmin);
    if (nextTab !== activeTab) {
      setActiveTab(nextTab);
      setShowAddProviderModal(false);
      setEditingProviderModels({});
    }
  }, [activeTab, isAdmin]);

  const handleSaveModels = async () => {
    try {
      setSaveStatus(prev => ({ ...prev, models: 'idle' }));
      // 将模型配置转换为字符串格式: "provider:model_name"
      const chatModelStr = chatModel.provider && chatModel.model_name
        ? `${chatModel.provider}:${chatModel.model_name}`
        : null;
      const writerModelStr = writerModel.provider && writerModel.model_name
        ? `${writerModel.provider}:${writerModel.model_name}`
        : null;

      const response = await fetch(`${apiUrl}/api/v1/settings/models`, {
        method: 'PUT',
        headers: await getAuthHeaders(),
        body: JSON.stringify({
          chat_model: chatModelStr,
          writer_model: writerModelStr,
          default_temperature: chatModel.temperature || 0.7,
          default_max_tokens: chatModel.max_tokens || 4000,
          default_top_p: 0.9
        })
      });
      if (response.status === 401) {
        handleAuthExpired();
        return;
      }
      if (!response.ok) {
        throw new Error(await getSettingsResponseError(response, '保存失败，请重试'));
      }
      showSuccess('保存成功');
      setSaveStatus(prev => ({ ...prev, models: 'success' }));
      setTimeout(() => setSaveStatus(prev => ({ ...prev, models: 'idle' })), 1500);
    } catch (error) {
      console.error('保存模型配置失败:', error);
      showError(error instanceof Error ? error.message : '保存失败，请重试');
      setSaveStatus(prev => ({ ...prev, models: 'idle' }));
    }
  };

  const handleSavePreferences = async () => {
    try {
      setSaveStatus(prev => ({ ...prev, preferences: 'idle' }));
      const response = await fetch(`${apiUrl}/api/v1/settings/preferences`, {
        method: 'PUT',
        headers: await getAuthHeaders(),
        body: JSON.stringify(preferences)
      });
      if (response.status === 401) {
        handleAuthExpired();
        return;
      }
      if (!response.ok) {
        throw new Error(await getSettingsResponseError(response, '保存失败，请重试'));
      }
      showSuccess('保存成功');
      setSaveStatus(prev => ({ ...prev, preferences: 'success' }));
      setTimeout(() => setSaveStatus(prev => ({ ...prev, preferences: 'idle' })), 1500);
    } catch (error) {
      console.error('保存偏好设置失败:', error);
      showError(error instanceof Error ? error.message : '保存失败，请重试');
      setSaveStatus(prev => ({ ...prev, preferences: 'idle' }));
    }
  };

  const handleUpdateProvider = (id: string, updates: Partial<LLMProvider>) => {
    setLlmProviders(prev => prev.map(p => p.id === id ? { ...p, ...updates } : p));
  };

  const handleAddProvider = async (providerId: string) => {
    try {
      const template = availableProviders.find(p => p.id === providerId);
      if (!template) return;

      const response = await fetch(`${apiUrl}/api/v1/settings/llm-providers`, {
        method: 'PUT',
        headers: await getAuthHeaders(),
        body: JSON.stringify({
          providers: llmProviders,
          operations: [{ action: 'add', provider_id: providerId }]
        })
      });

      if (response.status === 401) {
        handleAuthExpired();
        return;
      }

      const errorMessage = await getSettingsResponseError(response, '添加失败，请重试');
      if (errorMessage) {
        showError(errorMessage);
        return;
      }

      // 添加新提供商到本地状态
      const newProvider: LLMProvider = {
        id: template.id,
        name: template.name,
        base_url: template.base_url,
        models: template.default_models.map((name) => ({ name, min_tier: 'free' })),
        api_key: '',
        enabled: false
      };
      setLlmProviders(prev => [...prev, newProvider]);
      setShowAddProviderModal(false);
      showSuccess('提供商已添加');
    } catch (error) {
      console.error('添加提供商失败:', error);
      showError('添加失败，请重试');
    }
  };

  const handleDeleteProvider = async (providerId: string) => {
    // 确认删除
    setModalState({
      isOpen: true,
      title: '确认删除',
      message: `确定要删除此提供商吗？此操作不可撤销。`,
      type: 'confirm',
      onConfirm: async () => {
        try {
          const response = await fetch(`${apiUrl}/api/v1/settings/llm-providers`, {
            method: 'PUT',
            headers: await getAuthHeaders(),
            body: JSON.stringify({
              providers: llmProviders.filter(p => p.id !== providerId),
              operations: [{ action: 'remove', provider_id: providerId }]
            })
          });

          if (response.status === 401) {
            handleAuthExpired();
            return;
          }

          const errorMessage = await getSettingsResponseError(response, '删除失败，请重试');
          if (errorMessage) {
            showError(errorMessage);
            return;
          }

          setLlmProviders(prev => prev.filter(p => p.id !== providerId));
          showSuccess('提供商已删除');
        } catch (error) {
          console.error('删除提供商失败:', error);
          showError('删除失败，请重试');
        }
        setModalState({ isOpen: false, title: '', message: '', type: 'alert' });
      }
    });
  };

  const handleUpdateProviderModels = (providerId: string, models: LLMModel[]) => {
    setEditingProviderModels(prev => ({ ...prev, [providerId]: models }));
  };

  const handleSaveProviderModelsEdit = async () => {
    // 保存当前编辑状态的副本
    const modelsToSave = { ...editingProviderModels };

    // 保存到后端
    setSaveStatus(prev => ({ ...prev, llm: 'idle' }));
    if (!isAuthenticated) {
      showError('请先登录');
      return;
    }

    try {
      // 使用当前的 llmProviders 加上编辑中的更改来构建保存数据
      const providersToSave = buildLlmProvidersSavePayload(llmProviders, modelsToSave);

      const response = await fetch(`${apiUrl}/api/v1/settings/llm-providers`, {
        method: 'PUT',
        headers: await getAuthHeaders(),
        body: JSON.stringify({ providers: providersToSave })
      });

      if (response.status === 401) {
        handleAuthExpired();
        return;
      }
      const errorMessage = await getSettingsResponseError(response, '保存失败，请重试');
      if (errorMessage) {
        throw new Error(errorMessage);
      }

      setLlmProviders(prev => mergeProviderModelEdits(prev, modelsToSave));
      setEditingProviderModels({});
      showSuccess('LLM 提供商配置已保存');
      setSaveStatus(prev => ({ ...prev, llm: 'success' }));
      setTimeout(() => setSaveStatus(prev => ({ ...prev, llm: 'idle' })), 1500);
    } catch (error) {
      console.error('保存 LLM 提供商配置失败:', error);
      showError(error instanceof Error ? error.message : '保存失败，请重试');
      setSaveStatus(prev => ({ ...prev, llm: 'idle' }));
    }
  };

  const handleCancelModelsEdit = (providerId: string) => {
    // 取消编辑，移除该提供商的编辑状态
    setEditingProviderModels(prev => {
      const newState = { ...prev };
      delete newState[providerId];
      return newState;
    });
  };

  const handleSaveLLMProviders = async () => {
    try {
      setSaveStatus(prev => ({ ...prev, llm: 'idle' }));
      if (!isAuthenticated) {
        showError('请先登录');
        return;
      }
      
      // 过滤掉占位符密钥，只发送实际修改的密钥
      const providersToSave = buildLlmProvidersSavePayload(llmProviders);
      
      const response = await fetch(`${apiUrl}/api/v1/settings/llm-providers`, {
        method: 'PUT',
        headers: await getAuthHeaders(),
        body: JSON.stringify({ providers: providersToSave })
      });
      
      if (response.status === 401) {
        handleAuthExpired();
        return;
      }
      const errorMessage = await getSettingsResponseError(response, '保存失败，请重试');
      if (errorMessage) {
        throw new Error(errorMessage);
      }
      
      showSuccess('LLM 提供商配置已保存');
      setSaveStatus(prev => ({ ...prev, llm: 'success' }));
      setTimeout(() => setSaveStatus(prev => ({ ...prev, llm: 'idle' })), 1500);
    } catch (error) {
      console.error('保存 LLM 提供商配置失败:', error);
      showError(error instanceof Error ? error.message : '保存失败，请重试');
      setSaveStatus(prev => ({ ...prev, llm: 'idle' }));
    }
  };

  const handleSaveQiniuConfig = async () => {
    try {
      setSaveStatus(prev => ({ ...prev, qiniu: 'idle' }));
      if (!isAuthenticated) {
        showError('请先登录');
        return;
      }

      const response = await fetch(`${apiUrl}/api/v1/settings/services`, {
        method: 'PUT',
        headers: await getAuthHeaders(),
        body: JSON.stringify({
          qiniu_domain: qiniuConfig.domain,
          qiniu_folder: qiniuConfig.folder,
          qiniu_bucket: qiniuConfig.bucket,
          qiniu_access_key: qiniuConfig.accessKey,
          qiniu_secret_key: qiniuConfig.secretKey,
          qiniu_region: qiniuConfig.region
        })
      });

      if (response.status === 401) {
        handleAuthExpired();
        return;
      }
      const errorMessage = await getSettingsResponseError(response, '保存失败，请重试');
      if (errorMessage) {
        throw new Error(errorMessage);
      }

      showSuccess('七牛云配置已保存');
      setQiniuConfig(prev => ({ ...prev, keySet: !!(qiniuConfig.accessKey && qiniuConfig.secretKey) }));
      setSaveStatus(prev => ({ ...prev, qiniu: 'success' }));
      setTimeout(() => setSaveStatus(prev => ({ ...prev, qiniu: 'idle' })), 1500);
    } catch (error) {
      console.error('保存七牛云配置失败:', error);
      showError(error instanceof Error ? error.message : '保存失败，请重试');
      setSaveStatus(prev => ({ ...prev, qiniu: 'idle' }));
    }
  };

  const handleSaveSerperKey = async () => {
    try {
      setSaveStatus(prev => ({ ...prev, serper: 'idle' }));
      if (!isAuthenticated) {
        showError('请先登录');
        return;
      }
      
      const response = await fetch(`${apiUrl}/api/v1/settings/services`, {
        method: 'PUT',
        headers: await getAuthHeaders(),
        body: JSON.stringify({
          serper_api_key: serperApiKey
        })
      });
      
      if (response.status === 401) {
        handleAuthExpired();
        return;
      }
      const errorMessage = await getSettingsResponseError(response, '保存失败，请重试');
      if (errorMessage) {
        throw new Error(errorMessage);
      }
      
      showSuccess('SERPER API Key 已保存');
      setSerperKeySet(true);
      setSaveStatus(prev => ({ ...prev, serper: 'success' }));
      setTimeout(() => setSaveStatus(prev => ({ ...prev, serper: 'idle' })), 1500);
    } catch (error) {
      console.error('保存 SERPER API Key 失败:', error);
      showError(error instanceof Error ? error.message : '保存失败，请重试');
      setSaveStatus(prev => ({ ...prev, serper: 'idle' }));
    }
  };

  const handleSaveEmbeddingConfig = async () => {
    try {
      setSaveStatus(prev => ({ ...prev, embedding: 'idle' }));
      if (!isAuthenticated) {
        showError('请先登录');
        return;
      }

      const response = await fetch(`${apiUrl}/api/v1/settings/services`, {
        method: 'PUT',
        headers: await getAuthHeaders(),
        body: JSON.stringify({
          embedding_model: embeddingConfig.model,
          embedding_provider: embeddingConfig.provider,
          embedding_dimension: embeddingConfig.dimension,
          embedding_gitee_base_url: embeddingConfig.gitee_base_url,
          embedding_gitee_api_key: embeddingConfig.gitee_api_key,
        })
      });

      if (response.status === 401) {
        handleAuthExpired();
        return;
      }
      const errorMessage = await getSettingsResponseError(response, '保存失败，请重试');
      if (errorMessage) {
        throw new Error(errorMessage);
      }

      showSuccess('嵌入向量配置已保存');
      setEmbeddingConfig(prev => ({ ...prev, key_set: true, gitee_api_key: '' }));
      setSaveStatus(prev => ({ ...prev, embedding: 'success' }));
      setTimeout(() => setSaveStatus(prev => ({ ...prev, embedding: 'idle' })), 1500);
    } catch (error) {
      console.error('保存嵌入向量配置失败:', error);
      showError(error instanceof Error ? error.message : '保存失败，请重试');
      setSaveStatus(prev => ({ ...prev, embedding: 'idle' }));
    }
  };

  // 确保组件已挂载，避免 hydration 错误
  if (!mounted) {
    return (
      <MainLayout>
        <div className="max-w-[1376px] mx-auto">
          <div className="flex items-center justify-center py-12">
            <Loader2 className="animate-spin text-primary mr-4" size={48} />
          </div>
        </div>
      </MainLayout>
    );
  }

  // 如果 session 还在加载中，显示加载状态
  if (status === 'loading') {
    return (
      <MainLayout>
        <div className="max-w-[1376px] mx-auto">
          <SettingsStateCard mode="loading" statusText="正在加载用户信息..." />
        </div>
      </MainLayout>
    );
  }
  
  // 如果未登录，显示提示
  if (status === 'unauthenticated') {
    return (
      <MainLayout>
        <div className="max-w-[1376px] mx-auto">
          <SettingsStateCard mode="auth" signinHref={signInHref} />
        </div>
      </MainLayout>
    );
  }

  return (
    <MainLayout>
      <div className="max-w-[1376px] mx-auto">
        {/* 页面标题 */}
        <div className="flex items-center gap-3 mb-8">
          <span className="text-[32px]">⚙️</span>
          <div>
            <h1 className="font-heading text-[32px] font-semibold text-text-primary">
              系统设置
            </h1>
            <p className="font-body text-base text-text-secondary mt-1">
              管理 API 密钥、模型配置和个人偏好
            </p>
          </div>
        </div>

        <SettingsTabs activeTab={activeTab} isAdmin={isAdmin} onChange={setActiveTab} />

        {/* 内容区域 */}
        {loading ? (
          <Card padding="xl">
            <div className="flex flex-col items-center justify-center py-12">
              <Loader2 className="animate-spin text-primary mb-4" size={48} />
              <p className="text-text-secondary">加载中...</p>
            </div>
          </Card>
        ) : pageError ? (
          <Card padding="xl">
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <div className="w-14 h-14 rounded-2xl bg-red-50 text-red-500 flex items-center justify-center mb-4 text-2xl">
                !
              </div>
              <h2 className="text-xl font-semibold text-text-primary mb-2">系统设置加载失败</h2>
              <p className="text-text-secondary mb-6">{pageError}</p>
              <div className="flex items-center gap-3">
                <Button variant="secondary" onClick={() => router.push('/writer')}>
                  返回创作中心
                </Button>
                <Button variant="primary" onClick={() => loadSettings(activeTab)}>
                  重新加载
                </Button>
              </div>
            </div>
          </Card>
        ) : (
          <>
            {/* LLM 提供商配置 */}
            {isAdmin && activeTab === 'llm' && (
              <div className="space-y-4">
                <Card padding="lg">
                  <div className="flex items-center justify-between mb-6">
                    <div>
                      <h3 className="font-heading text-lg font-semibold text-text-primary">
                        LLM 提供商配置
                      </h3>
                      <p className="text-sm text-text-secondary mt-1">
                        配置各个 LLM 提供商的 API 密钥和模型列表
                      </p>
                    </div>
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => setShowAddProviderModal(true)}
                    >
                      <Plus size={16} className="mr-2" />
                      添加提供商
                    </Button>
                  </div>

                  <div className="space-y-4">
                    {llmProviders.map((provider) => {
                      const isEditing = editingProviderModels[provider.id] !== undefined;
                      const currentModels = isEditing ? editingProviderModels[provider.id] : provider.models;

                      return (
                        <div key={provider.id} className="border border-border rounded-lg overflow-hidden">
                          {/* 提供商名称标题栏 */}
                          <div className="bg-bg px-4 py-2 border-b border-border flex items-center justify-between">
                            <span className="font-body text-sm font-bold text-text-primary uppercase tracking-wide">
                              {provider.id}
                            </span>
                            <Badge variant={provider.enabled ? 'primary' : 'default'}>
                              {provider.enabled ? '已启用' : '未启用'}
                            </Badge>
                          </div>

                          {/* 内容区域 */}
                          <div className="p-4">
                            <div className="flex items-start justify-between mb-4">
                              <div className="flex items-center gap-3">
                                <h4 className="font-body text-base font-semibold text-text-primary">
                                  {provider.name}
                                </h4>
                              </div>
                            <div className="flex items-center gap-2">
                              <button
                                onClick={() => handleDeleteProvider(provider.id)}
                                className="p-2 text-red-500 hover:text-red-700 hover:bg-red-50 rounded transition-colors"
                                title="删除提供商"
                              >
                                <Trash2 size={16} />
                              </button>
                              <label className="relative inline-flex items-center cursor-pointer">
                                <input
                                  type="checkbox"
                                  checked={provider.enabled}
                                  onChange={(e) => handleUpdateProvider(provider.id, { enabled: e.target.checked })}
                                  className="sr-only peer"
                                />
                                <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary/20 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary"></div>
                              </label>
                            </div>
                          </div>

                          <div className="space-y-3">
                            <div>
                              <label className="block text-sm font-medium text-text-primary mb-1">
                                Base URL
                              </label>
                              <input
                                type="text"
                                value={provider.base_url}
                                onChange={(e) => handleUpdateProvider(provider.id, { base_url: e.target.value })}
                                className="w-full px-3 py-2 border border-border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                                placeholder="https://api.example.com/v1"
                              />
                            </div>

                            <div>
                              <label className="block text-sm font-medium text-text-primary mb-1">
                                API Key
                              </label>
                              <div className="relative">
                                <input
                                  type={showProviderKeys[provider.id] ? 'text' : 'password'}
                                  value={provider.api_key}
                                  onChange={(e) => handleUpdateProvider(provider.id, { api_key: e.target.value })}
                                  className="w-full px-3 py-2 pr-10 border border-border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                                  placeholder="sk-..."
                                />
                                <button
                                  type="button"
                                  onClick={() => setShowProviderKeys(prev => ({ ...prev, [provider.id]: !prev[provider.id] }))}
                                  className="absolute right-3 top-1/2 -translate-y-1/2 text-text-secondary hover:text-text-primary transition-colors"
                                >
                                  {showProviderKeys[provider.id] ? <EyeOff size={18} /> : <Eye size={18} />}
                                </button>
                              </div>
                            </div>

                            <div>
                              <div className="flex items-center justify-between mb-2">
                                <label className="block text-sm font-medium text-text-primary">
                                  支持的模型
                                </label>
                                <button
                                  onClick={() => {
                                    if (isEditing) {
                                      handleSaveProviderModelsEdit();
                                    } else {
                                      setEditingProviderModels(prev => ({ ...prev, [provider.id]: [...provider.models] }));
                                    }
                                  }}
                                  className="text-xs text-primary hover:underline"
                                >
                                  {isEditing ? '完成' : '编辑'}
                                </button>
                              </div>

                              {isEditing ? (
                                // 编辑模式
                                <div className="p-3 bg-bg rounded-lg space-y-2">
                                  {currentModels.map((model, idx) => (
                                    <div key={idx} className="flex items-center gap-2">
                                      <input
                                        type="text"
                                        value={typeof model === 'string' ? model : model.name}
                                        onChange={(e) => {
                                          const newModels = [...currentModels];
                                          if (typeof model === 'string') {
                                            newModels[idx] = { name: e.target.value, min_tier: 'free' };
                                          } else {
                                            newModels[idx] = { ...model, name: e.target.value };
                                          }
                                          setEditingProviderModels(prev => ({ ...prev, [provider.id]: newModels }));
                                        }}
                                        className="flex-1 px-3 py-2 text-sm border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                                      />
                                      <select
                                        value={typeof model === 'string' ? 'free' : model.min_tier}
                                        onChange={(e) => {
                                          const newModels = [...currentModels];
                                          if (typeof model === 'string') {
                                            newModels[idx] = { name: model, min_tier: e.target.value };
                                          } else {
                                            newModels[idx] = { ...model, min_tier: e.target.value };
                                          }
                                          setEditingProviderModels(prev => ({ ...prev, [provider.id]: newModels }));
                                        }}
                                        className="w-24 px-2 py-2 text-sm border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                                      >
                                        <option value="free">Free</option>
                                        <option value="pro">Pro</option>
                                        <option value="ultra">Ultra</option>
                                      </select>
                                      <button
                                        onClick={() => {
                                          const newModels = currentModels.filter((_, i) => i !== idx);
                                          setEditingProviderModels(prev => ({ ...prev, [provider.id]: newModels }));
                                        }}
                                        className="p-2 text-red-500 hover:text-red-700 rounded"
                                      >
                                        <Trash2 size={14} />
                                      </button>
                                    </div>
                                  ))}
                                  <button
                                    onClick={() => {
                                      setEditingProviderModels(prev => ({ ...prev, [provider.id]: [...currentModels, { name: '', min_tier: 'free' }] }));
                                    }}
                                    className="w-full px-3 py-2 text-sm border border-dashed border-border rounded-lg text-text-secondary hover:border-primary hover:text-primary transition-colors"
                                  >
                                    + 添加模型
                                  </button>
                                </div>
                              ) : (
                                // 显示模式
                                <div className="flex flex-wrap gap-2">
                                  {provider.models.length > 0 ? (
                                    provider.models.map((model, idx) => (
                                      <span
                                        key={idx}
                                        className="px-3 py-1 bg-bg text-text-secondary text-xs rounded-full flex items-center gap-1"
                                      >
                                        {model.name}
                                        {model.min_tier !== 'free' && (
                                          <span className="text-[10px] px-1 py-0.5 bg-primary/10 text-primary rounded">
                                            {model.min_tier}
                                          </span>
                                        )}
                                      </span>
                                    ))
                                  ) : (
                                    <span className="text-sm text-text-secondary">暂无模型</span>
                                  )}
                                </div>
                              )}
                            </div>
                          </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>

                  <div className="mt-6">
                    <Button
                      variant={saveStatus.llm === 'success' ? 'secondary' : 'primary'}
                      size="lg"
                      onClick={handleSaveLLMProviders}
                      className={`w-full ${saveStatus.llm === 'success' ? 'bg-green-500 text-white border-green-500 hover:bg-green-600' : ''}`}
                      disabled={saveStatus.llm === 'success'}
                    >
                      {saveStatus.llm === 'success' ? (
                        <>
                          <Check size={18} />
                          已保存
                        </>
                      ) : '保存 LLM 配置'}
                    </Button>
                  </div>
                </Card>
              </div>
            )}

            {/* 其他服务配置 */}
            {isAdmin && activeTab === 'services' && (
              <div className="space-y-4">
                {/* 七牛云配置 */}
                <Card padding="lg">
                  <div className="mb-6">
                    <h3 className="font-heading text-lg font-semibold text-text-primary">
                      七牛云存储配置
                    </h3>
                    <p className="text-sm text-text-secondary mt-1">
                      用于图片和文件存储，获取密钥请前往
                      <a href="https://portal.qiniu.com/user/key" target="_blank" rel="noopener noreferrer" className="text-primary hover:underline ml-1">七牛云控制台</a>
                    </p>
                  </div>

                  <div className="space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-text-primary mb-1">
                          CDN 域名 (Domain)
                        </label>
                        <p className="text-xs text-text-tertiary mb-2">
                          绑定到七牛存储空间的 CDN 加速域名，如 http://cdn.example.com/
                        </p>
                        <input
                          type="text"
                          value={qiniuConfig.domain}
                          onChange={(e) => setQiniuConfig({ ...qiniuConfig, domain: e.target.value })}
                          className="w-full px-3 py-2 border border-border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                          placeholder="http://cdn.example.com/"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-text-primary mb-1">
                          存储路径 (Folder)
                        </label>
                        <p className="text-xs text-text-tertiary mb-2">
                          文件在存储空间中的前缀路径，如 images/ 或 supawriter/
                        </p>
                        <input
                          type="text"
                          value={qiniuConfig.folder}
                          onChange={(e) => setQiniuConfig({ ...qiniuConfig, folder: e.target.value })}
                          className="w-full px-3 py-2 border border-border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                          placeholder="supawriter/"
                        />
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-text-primary mb-1">
                          Access Key
                        </label>
                        <p className="text-xs text-text-tertiary mb-2">
                          七牛云账号的 AccessKey，用于身份验证
                        </p>
                        <input
                          type="text"
                          value={qiniuConfig.accessKey}
                          onChange={(e) => setQiniuConfig({ ...qiniuConfig, accessKey: e.target.value })}
                          className="w-full px-3 py-2 border border-border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary font-mono"
                          placeholder="请输入 Access Key"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-text-primary mb-1">
                          Secret Key
                        </label>
                        <p className="text-xs text-text-tertiary mb-2">
                          七牛云账号的 SecretKey，与 AccessKey 配对使用
                        </p>
                        <input
                          type="text"
                          value={qiniuConfig.secretKey}
                          onChange={(e) => setQiniuConfig({ ...qiniuConfig, secretKey: e.target.value })}
                          className="w-full px-3 py-2 border border-border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary font-mono"
                          placeholder="请输入 Secret Key"
                        />
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-text-primary mb-1">
                          存储空间 (Bucket)
                        </label>
                        <p className="text-xs text-text-tertiary mb-2">
                          七牛云对象存储的空间名称
                        </p>
                        <input
                          type="text"
                          value={qiniuConfig.bucket}
                          onChange={(e) => setQiniuConfig({ ...qiniuConfig, bucket: e.target.value })}
                          className="w-full px-3 py-2 border border-border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                          placeholder="my-bucket"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-text-primary mb-1">
                          存储区域 (Region)
                        </label>
                        <p className="text-xs text-text-tertiary mb-2">
                          选择您七牛云存储空间所在的区域
                        </p>
                        <select
                          value={qiniuConfig.region}
                          onChange={(e) => setQiniuConfig({ ...qiniuConfig, region: e.target.value })}
                          className="w-full px-3 py-2 border border-border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                        >
                          <option value="z0">华东 (z0) - 杭州</option>
                          <option value="z1">华北 (z1) - 河北</option>
                          <option value="z2">华南 (z2) - 广东</option>
                          <option value="na0">北美 (na0) - 洛杉矶</option>
                          <option value="as0">东南亚 (as0) - 新加坡</option>
                          <option value="cn-east-2">华东-浙江2 (cn-east-2)</option>
                        </select>
                      </div>
                    </div>

                    <Button
                      variant={saveStatus.qiniu === 'success' ? 'secondary' : 'primary'}
                      size="lg"
                      onClick={handleSaveQiniuConfig}
                      className={`w-full ${saveStatus.qiniu === 'success' ? 'bg-green-500 text-white border-green-500 hover:bg-green-600' : ''}`}
                      disabled={saveStatus.qiniu === 'success'}
                    >
                      {saveStatus.qiniu === 'success' ? (
                        <>
                          <Check size={18} />
                          已保存
                        </>
                      ) : '保存七牛云配置'}
                    </Button>
                  </div>
                </Card>

                {/* SERPER 搜索配置 */}
                <Card padding="lg">
                  <div className="mb-6">
                    <h3 className="font-heading text-lg font-semibold text-text-primary">
                      SERPER 搜索 API
                    </h3>
                    <p className="text-sm text-text-secondary mt-1">
                      用于网络搜索功能，获取 API Key 请前往
                      <a href="https://serper.dev/" target="_blank" rel="noopener noreferrer" className="text-primary hover:underline ml-1">serper.dev</a>
                    </p>
                  </div>

                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-text-primary mb-1">
                        API Key
                      </label>
                      <p className="text-xs text-text-tertiary mb-2">
                        Serper 提供 Google 搜索结果 API，用于文章生成时的资料搜索。免费版每月 2500 次调用。
                      </p>
                      <input
                        type="text"
                        value={serperApiKey}
                        onChange={(e) => setSerperApiKey(e.target.value)}
                        className="w-full px-3 py-2 border border-border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary font-mono"
                        placeholder="请输入 SERPER API Key"
                      />
                    </div>

                    <Button
                      variant={saveStatus.serper === 'success' ? 'secondary' : 'primary'}
                      size="lg"
                      onClick={handleSaveSerperKey}
                      className={`w-full ${saveStatus.serper === 'success' ? 'bg-green-500 text-white border-green-500 hover:bg-green-600' : ''}`}
                      disabled={saveStatus.serper === 'success'}
                    >
                      {saveStatus.serper === 'success' ? (
                        <>
                          <Check size={18} />
                          已保存
                        </>
                      ) : '保存 SERPER API Key'}
                    </Button>
                  </div>
                </Card>

                {/* 嵌入向量模型配置 */}
                <Card padding="lg">
                  <div className="mb-6">
                    <h3 className="font-heading text-lg font-semibold text-text-primary">
                      嵌入向量模型配置
                    </h3>
                    <p className="text-sm text-text-secondary mt-1">
                      用于文章图片语义匹配的嵌入向量模型，支持图片和文本的多模态嵌入
                    </p>
                  </div>

                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-text-primary mb-1">
                        嵌入模型
                      </label>
                      <select
                        value={embeddingConfig.model}
                        onChange={(e) => {
                          const model = e.target.value;
                          const dims: Record<string, string> = {
                            'Qwen3-VL-Embedding-8B': '4096',
                            'Qwen3-VL-Embedding-2B': '1024',
                            'jina-embeddings-v4': '2048',
                          };
                          setEmbeddingConfig({
                            ...embeddingConfig,
                            model,
                            dimension: dims[model] || embeddingConfig.dimension,
                          });
                        }}
                        className="w-full h-12 px-4 bg-surface border-[1.5px] border-border rounded-lg font-body text-[15px] text-text-primary focus:border-primary focus:outline-none focus:ring-3 focus:ring-primary/10 transition-all"
                      >
                        <option value="Qwen3-VL-Embedding-8B">Qwen3-VL-Embedding-8B (推荐，4096维)</option>
                        <option value="Qwen3-VL-Embedding-2B">Qwen3-VL-Embedding-2B (轻量，1024维)</option>
                        <option value="jina-embeddings-v4">jina-embeddings-v4 (2048维)</option>
                      </select>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-text-primary mb-1">
                          向量维度
                        </label>
                        <input
                          type="text"
                          value={embeddingConfig.dimension}
                          onChange={(e) => setEmbeddingConfig({ ...embeddingConfig, dimension: e.target.value })}
                          className="w-full px-3 py-2 border border-border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary font-mono"
                          placeholder="4096"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-text-primary mb-1">
                          Base URL
                        </label>
                        <input
                          type="text"
                          value={embeddingConfig.gitee_base_url}
                          onChange={(e) => setEmbeddingConfig({ ...embeddingConfig, gitee_base_url: e.target.value })}
                          className="w-full px-3 py-2 border border-border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary font-mono"
                          placeholder="https://ai.gitee.com/v1"
                        />
                      </div>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-text-primary mb-1">
                        API Key
                      </label>
                      <p className="text-xs text-text-tertiary mb-2">
                        {embeddingConfig.key_set ? '密钥已设置，留空则保持不变' : '请输入嵌入向量服务的 API Key'}
                      </p>
                      <div className="relative">
                        <input
                          type={showEmbeddingKey ? 'text' : 'password'}
                          value={embeddingConfig.gitee_api_key}
                          onChange={(e) => setEmbeddingConfig({ ...embeddingConfig, gitee_api_key: e.target.value })}
                          className="w-full px-3 py-2 border border-border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary font-mono pr-10"
                          placeholder={embeddingConfig.key_set ? '••••••••' : '请输入 API Key'}
                        />
                        <button
                          type="button"
                          onClick={() => setShowEmbeddingKey(!showEmbeddingKey)}
                          className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-text-secondary hover:text-text-primary"
                        >
                          {showEmbeddingKey ? <EyeOff size={16} /> : <Eye size={16} />}
                        </button>
                      </div>
                    </div>

                    <Button
                      variant={saveStatus.embedding === 'success' ? 'secondary' : 'primary'}
                      size="lg"
                      onClick={handleSaveEmbeddingConfig}
                      className={`w-full ${saveStatus.embedding === 'success' ? 'bg-green-500 text-white border-green-500 hover:bg-green-600' : ''}`}
                      disabled={saveStatus.embedding === 'success'}
                    >
                      {saveStatus.embedding === 'success' ? (
                        <>
                          <Check size={18} />
                          已保存
                        </>
                      ) : '保存嵌入向量配置'}
                    </Button>
                  </div>
                </Card>
              </div>
            )}

            {/* 模型配置 */}
            {activeTab === 'models' && (
              <Card padding="xl">
                <div className="space-y-6">
                  <div>
                    <h3 className="font-heading text-lg font-semibold text-text-primary mb-4">
                      Chat 模型
                    </h3>
                    <div className="space-y-3">
                      <div>
                        <label className="block text-sm font-medium text-text-primary mb-2">
                          提供商
                        </label>
                        <select
                          value={chatModel.provider}
                          onChange={(e) => {
                            const provider = llmProviders.find(p => p.id === e.target.value);
                            setChatModel({
                              ...chatModel,
                              provider: e.target.value,
                              model_name: provider?.models?.[0]?.name || ''
                            });
                          }}
                          className="w-full h-12 px-4 bg-surface border-[1.5px] border-border rounded-lg font-body text-[15px] text-text-primary focus:border-primary focus:outline-none focus:ring-3 focus:ring-primary/10 transition-all"
                          style={{ color: '#1a1a1a' }}
                        >
                          <option value="" style={{ color: '#666' }}>请选择提供商</option>
                          {llmProviders.filter(p => p.enabled).map((provider) => (
                            <option key={provider.id} value={provider.id} style={{ color: '#1a1a1a' }}>
                              {provider.name || provider.id}
                            </option>
                          ))}
                        </select>
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-text-primary mb-2">
                          模型名称
                        </label>
                        <select
                          value={chatModel.model_name}
                          onChange={(e) => setChatModel({ ...chatModel, model_name: e.target.value })}
                          className="w-full h-12 px-4 bg-surface border-[1.5px] border-border rounded-lg font-body text-[15px] text-text-primary focus:border-primary focus:outline-none focus:ring-3 focus:ring-primary/10 transition-all"
                          style={{ color: '#1a1a1a' }}
                          disabled={!chatModel.provider}
                        >
                          <option value="" style={{ color: '#666' }}>请选择模型</option>
                          {llmProviders
                            .find(p => p.id === chatModel.provider)
                            ?.models.map((model) => (
                              <option key={model.name} value={model.name} style={{ color: '#1a1a1a' }}>
                                {model.name}
                              </option>
                            ))}
                        </select>
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-text-primary mb-2">
                          温度 (0-1)
                        </label>
                        <input
                          type="number"
                          step="0.1"
                          min="0"
                          max="1"
                          value={chatModel.temperature || 0.7}
                          onChange={(e) => setChatModel({ ...chatModel, temperature: parseFloat(e.target.value) })}
                          className="w-full h-12 px-4 bg-surface border-[1.5px] border-border rounded-lg font-body text-[15px] text-text-primary focus:border-primary focus:outline-none focus:ring-3 focus:ring-primary/10 transition-all"
                        />
                      </div>
                    </div>
                  </div>

                  <div>
                    <h3 className="font-heading text-lg font-semibold text-text-primary mb-4">
                      Writer 模型
                    </h3>
                    <div className="space-y-3">
                      <div>
                        <label className="block text-sm font-medium text-text-primary mb-2">
                          提供商
                        </label>
                        <select
                          value={writerModel.provider}
                          onChange={(e) => {
                            const provider = llmProviders.find(p => p.id === e.target.value);
                            setWriterModel({
                              ...writerModel,
                              provider: e.target.value,
                              model_name: provider?.models?.[0]?.name || ''
                            });
                          }}
                          className="w-full h-12 px-4 bg-surface border-[1.5px] border-border rounded-lg font-body text-[15px] text-text-primary focus:border-primary focus:outline-none focus:ring-3 focus:ring-primary/10 transition-all"
                          style={{ color: '#1a1a1a' }}
                        >
                          <option value="" style={{ color: '#666' }}>请选择提供商</option>
                          {llmProviders.filter(p => p.enabled).map((provider) => (
                            <option key={provider.id} value={provider.id} style={{ color: '#1a1a1a' }}>
                              {provider.name || provider.id}
                            </option>
                          ))}
                        </select>
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-text-primary mb-2">
                          模型名称
                        </label>
                        <select
                          value={writerModel.model_name}
                          onChange={(e) => setWriterModel({ ...writerModel, model_name: e.target.value })}
                          className="w-full h-12 px-4 bg-surface border-[1.5px] border-border rounded-lg font-body text-[15px] text-text-primary focus:border-primary focus:outline-none focus:ring-3 focus:ring-primary/10 transition-all"
                          style={{ color: '#1a1a1a' }}
                          disabled={!writerModel.provider}
                        >
                          <option value="" style={{ color: '#666' }}>请选择模型</option>
                          {llmProviders
                            .find(p => p.id === writerModel.provider)
                            ?.models.map((model) => (
                              <option key={model.name} value={model.name} style={{ color: '#1a1a1a' }}>
                                {model.name}
                              </option>
                            ))}
                        </select>
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-text-primary mb-2">
                          温度 (0-1)
                        </label>
                        <input
                          type="number"
                          step="0.1"
                          min="0"
                          max="1"
                          value={writerModel.temperature || 0.7}
                          onChange={(e) => setWriterModel({ ...writerModel, temperature: parseFloat(e.target.value) })}
                          className="w-full h-12 px-4 bg-surface border-[1.5px] border-border rounded-lg font-body text-[15px] text-text-primary focus:border-primary focus:outline-none focus:ring-3 focus:ring-primary/10 transition-all"
                        />
                      </div>
                    </div>
                  </div>

                  <Button
                    variant={saveStatus.models === 'success' ? 'secondary' : 'primary'}
                    size="lg"
                    onClick={handleSaveModels}
                    className={`w-full ${saveStatus.models === 'success' ? 'bg-green-500 text-white border-green-500 hover:bg-green-600' : ''}`}
                    disabled={saveStatus.models === 'success'}
                  >
                    {saveStatus.models === 'success' ? (
                      <>
                        <Check size={18} />
                        已保存
                      </>
                    ) : '保存模型配置'}
                  </Button>
                </div>
              </Card>
            )}

            {/* 个人偏好 */}
            {activeTab === 'preferences' && (
              <PreferencesSettings
                preferences={preferences}
                saveSuccess={saveStatus.preferences === 'success'}
                onChange={setPreferences}
                onSave={handleSavePreferences}
              />
            )}

            {/* 风格学习 */}
            {activeTab === 'style' && (
              <Card padding="xl">
                <StyleLearning />
              </Card>
            )}

            {/* 订阅管理 */}
            {activeTab === 'subscription' && (
              <SubscriptionManagement />
            )}
          </>
        )}

        {/* 管理员功能链接 */}
        {isAdmin && (
          <div className="mt-8 pt-8 border-t border-border">
            <h3 className="font-heading text-lg font-semibold text-text-primary mb-4">
              管理功能
            </h3>
            <div className="grid grid-cols-2 gap-4">
              <a href="/settings/admin/tier-config" className="block p-4 bg-bg rounded-lg hover:bg-bg-alt transition-all">
                <div className="font-body text-base font-semibold text-text-primary">等级配置</div>
                <div className="text-sm text-text-secondary mt-1">配置各等级的模型权限和默认值</div>
              </a>
              <a href="/settings/admin/user-management" className="block p-4 bg-bg rounded-lg hover:bg-bg-alt transition-all">
                <div className="font-body text-base font-semibold text-text-primary">用户管理</div>
                <div className="text-sm text-text-secondary mt-1">搜索用户并管理会员等级</div>
              </a>
            </div>
          </div>
        )}
      </div>

      {/* Modal */}
      <Modal
        isOpen={modalState.isOpen}
        onClose={() => setModalState({ ...modalState, isOpen: false })}
        onConfirm={modalState.onConfirm}
        title={modalState.title}
        message={modalState.message}
        type={modalState.type}
      />

      {/* 添加提供商模态框 */}
      {showAddProviderModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[80vh] overflow-auto">
            <div className="flex items-center justify-between p-4 border-b">
              <h3 className="text-lg font-semibold">添加 LLM 提供商</h3>
              <button
                onClick={() => setShowAddProviderModal(false)}
                className="p-2 hover:bg-gray-100 rounded"
              >
                <X size={20} />
              </button>
            </div>
            <div className="p-4">
              <div className="grid grid-cols-2 gap-4">
                {availableProviders
                  .filter(p => !llmProviders.find(up => up.id === p.id))
                  .map(template => (
                    <div
                      key={template.id}
                      onClick={() => handleAddProvider(template.id)}
                      className="border border-border rounded-lg p-4 cursor-pointer hover:border-primary hover:bg-primary/5 transition-all"
                    >
                      <h4 className="font-semibold text-text-primary">{template.name}</h4>
                      <p className="text-sm text-text-secondary mt-1">{template.description}</p>
                      <div className="flex flex-wrap gap-1 mt-3">
                        {template.default_models.slice(0, 3).map(model => (
                          <span key={model} className="text-xs bg-bg px-2 py-1 rounded">
                            {model}
                          </span>
                        ))}
                        {template.default_models.length > 3 && (
                          <span className="text-xs text-text-secondary">
                            +{template.default_models.length - 3} 更多
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
              </div>
              {availableProviders.filter(p => !llmProviders.find(up => up.id === p.id)).length === 0 && (
                <div className="text-center py-8 text-text-secondary">
                  没有可添加的提供商
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </MainLayout>
  );
}
