'use client';

import { useSharedAuth } from '@/contexts/AuthContext';
import { useModelConfig } from '@/contexts/ModelConfigContext';

export interface CapabilityReadiness {
  ready: boolean;
  loading: boolean;
  reason?: 'missing_provider' | 'missing_model' | 'unauthenticated';
  title: string;
  description: string;
  ctaHref: '/settings' | '/pricing' | '/auth/signin';
  ctaLabel: string;
}

function createMissingConfigState(): CapabilityReadiness {
  return {
    ready: false,
    loading: false,
    reason: 'missing_model',
    title: '请先完成能力配置',
    description: '当前账号尚未配置可用的模型或 API Key，请先到系统设置完成配置后再使用此功能。',
    ctaHref: '/settings',
    ctaLabel: '前往设置',
  };
}

export function useCapabilityReadiness(capability: 'chat' | 'writer'): CapabilityReadiness {
  const { isAuthenticated } = useSharedAuth();
  const { config, loading } = useModelConfig();

  if (!isAuthenticated) {
    return {
      ready: false,
      loading: false,
      reason: 'unauthenticated',
      title: '请先登录',
      description: '登录后才能继续使用此功能。',
      ctaHref: '/auth/signin',
      ctaLabel: '前往登录',
    };
  }

  if (loading) {
    return {
      ready: false,
      loading: true,
      reason: 'unauthenticated',
      title: '请先登录',
      description: '登录后才能继续使用此功能。',
      ctaHref: '/auth/signin',
      ctaLabel: '前往登录',
    };
  }

  const model = capability === 'chat' ? config.chat_model : config.writer_model;
  if (!model) {
    return createMissingConfigState();
  }

  return {
    ready: true,
    loading: false,
    title: '',
    description: '',
    ctaHref: '/settings',
    ctaLabel: '前往设置',
  };
}
