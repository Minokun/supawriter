import { apiClient } from './client';

export interface PricingPlan {
  id: string;
  name: string;
  prices: {
    monthly: number;
    quarterly: number;
    yearly: number;
  };
  features: string[];
  quota: number;
  popular?: boolean;
}

export interface QuotaPack {
  id: string;
  quota: number;
  price: number;
}

export interface QuotaInfo {
  plan_quota: number;
  plan_used: number;
  plan_remaining: number;
  pack_quota: number;
  pack_used: number;
  pack_remaining: number;
  total_remaining: number;
}

export interface PricingResponse {
  plans: PricingPlan[];
  quota_packs: QuotaPack[];
}

export interface SubscriptionResponse {
  feature_tier: string;
  billing_plan?: string | null;
  has_active_subscription: boolean;
  current_plan: string;
  current_period: string | null;
  status: string;
  current_period_start: string | null;
  current_period_end: string | null;
  auto_renew: boolean;
  quota: {
    monthly_limit: number;
    monthly_used: number;
    pack_remaining: number;
  };
}

export class PricingApi {
  async getPlans(): Promise<PricingResponse> {
    return apiClient.get('/api/v1/pricing/plans');
  }

  async getQuotaPacks(): Promise<{ quota_packs: QuotaPack[] }> {
    return apiClient.get('/api/v1/pricing/quota-packs');
  }
}

export class SubscriptionApi {
  async get(): Promise<SubscriptionResponse> {
    return apiClient.get('/api/v1/subscription');
  }

  async upgrade(plan: string, period: string): Promise<{ order_id: string; status: string; amount: number; message: string }> {
    return apiClient.post('/api/v1/subscription/upgrade', { plan, period });
  }

  async cancel(): Promise<{ message: string; current_period_end: string }> {
    return apiClient.post('/api/v1/subscription/cancel');
  }
}

export class QuotaApi {
  async get(): Promise<QuotaInfo> {
    return apiClient.get('/api/v1/subscription/quota');
  }

  async purchasePack(packType: string): Promise<{ order_id: string; status: string; amount: number }> {
    return apiClient.post('/api/v1/subscription/quota-packs/purchase', { pack_type: packType });
  }
}

export const pricingApi = new PricingApi();
export const subscriptionApi = new SubscriptionApi();
export const quotaApi = new QuotaApi();
