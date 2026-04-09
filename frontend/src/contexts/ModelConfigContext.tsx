'use client';

import { createContext, useContext, useState, useEffect, useCallback, useRef, ReactNode } from 'react';
import { useSession } from 'next-auth/react';
import { getBackendToken } from '@/lib/api';
import { getSessionCache, setSessionCache } from '@/lib/session-cache';
import { getApiBaseUrl } from '@/lib/api-base-url';

export interface ModelConfig {
  chat_model: string;
  writer_model: string;
}

const DEFAULT_CONFIG: ModelConfig = {
  chat_model: 'longcat:LongCat-Flash-Chat',
  writer_model: 'longcat:LongCat-Flash-Chat',
};

const CACHE_KEY = 'modelConfig';
const CACHE_TTL = 5 * 60 * 1000; // 5 minutes

interface ModelConfigContextType {
  config: ModelConfig;
  loading: boolean;
  refetch: () => Promise<ModelConfig | null>;
}

const ModelConfigContext = createContext<ModelConfigContextType | undefined>(undefined);

// Module-level promise singleton: deduplicates concurrent fetch calls within same tick
let fetchPromise: Promise<ModelConfig | null> | null = null;

async function fetchModelConfig(): Promise<ModelConfig | null> {
  if (fetchPromise) return fetchPromise;

  fetchPromise = (async () => {
    try {
      const token = await getBackendToken();
      const apiBaseUrl = getApiBaseUrl();
      const response = await fetch(`${apiBaseUrl}/api/v1/settings/models`, {
        headers: token ? { Authorization: `Bearer ${token}` } : undefined,
      });

      if (!response.ok) return null;

      const data = await response.json();
      if (!data?.chat_model && !data?.writer_model) return null;

      const config: ModelConfig = {
        chat_model: data.chat_model || DEFAULT_CONFIG.chat_model,
        writer_model: data.writer_model || DEFAULT_CONFIG.writer_model,
      };
      setSessionCache(CACHE_KEY, config);
      return config;
    } catch {
      return null;
    } finally {
      fetchPromise = null;
    }
  })();

  return fetchPromise;
}

export function ModelConfigProvider({ children }: { children: ReactNode }) {
  const { status: sessionStatus } = useSession();
  const [config, setConfig] = useState<ModelConfig>(() => {
    const cached = getSessionCache<ModelConfig>(CACHE_KEY, CACHE_TTL);
    return cached || DEFAULT_CONFIG;
  });
  const [loading, setLoading] = useState(() => !getSessionCache<ModelConfig>(CACHE_KEY, CACHE_TTL));
  const hasFetched = useRef(false);

  const loadConfig = useCallback(async (forceRefresh = false) => {
    if (!forceRefresh) {
      const cached = getSessionCache<ModelConfig>(CACHE_KEY, CACHE_TTL);
      if (cached) {
        setConfig(cached);
        setLoading(false);
        hasFetched.current = true;
        return cached;
      }
    }

    setLoading(true);
    const result = await fetchModelConfig();
    if (result) {
      setConfig(result);
    }
    setLoading(false);
    hasFetched.current = true;
    return result;
  }, []);

  // Fetch once when authenticated
  useEffect(() => {
    if (sessionStatus === 'unauthenticated') return;
    if (hasFetched.current) return;

    // Check cache first
    const cached = getSessionCache<ModelConfig>(CACHE_KEY, CACHE_TTL);
    if (cached) {
      setConfig(cached);
      setLoading(false);
      hasFetched.current = true;
      return;
    }

    loadConfig();
  }, [sessionStatus, loadConfig]);

  const refetch = useCallback(async () => {
    return loadConfig(true);
  }, [loadConfig]);

  return (
    <ModelConfigContext.Provider value={{ config, loading, refetch }}>
      {children}
    </ModelConfigContext.Provider>
  );
}

export function useModelConfig(): ModelConfigContextType {
  const ctx = useContext(ModelConfigContext);
  if (!ctx) throw new Error('useModelConfig must be used within ModelConfigProvider');
  return ctx;
}
