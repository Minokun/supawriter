'use client';

import { useState, useEffect } from 'react';
import { useAuth } from '@/hooks/useAuth';
import MainLayout from '@/components/layout/MainLayout';
import Card from '@/components/ui/Card';
import Button from '@/components/ui/Button';
import Input from '@/components/ui/Input';
import Badge from '@/components/ui/Badge';
import { Settings, Plus, Trash2, Save, Loader2 } from 'lucide-react';
import { useToast } from '@/components/ui/ToastContainer';
import {
  getAllTierDefaults,
  updateTierDefaults,
  getGlobalProviders,
  updateGlobalProvider,
  deleteGlobalProvider
} from '@/lib/api';
import type { MembershipTier, TierModelConfig, GlobalLLMProvider, TierDefaults, AllTierDefaults } from '@/types/api';

const TIERS: MembershipTier[] = ['free', 'pro', 'ultra', 'superuser'];

const TIER_NAMES: Record<MembershipTier, string> = {
  free: 'Free',
  pro: 'Pro',
  ultra: 'Ultra',
  superuser: 'Superuser'
};

const TIER_COLORS: Record<MembershipTier, string> = {
  free: 'bg-gray-100 text-gray-700',
  pro: 'bg-blue-100 text-blue-700',
  ultra: 'bg-purple-100 text-purple-700',
  superuser: 'bg-red-100 text-red-700'
};

export default function TierConfigPage() {
  const { isAuthenticated, isAdmin } = useAuth();
  const { showSuccess, showError } = useToast();
  const [mounted, setMounted] = useState(false);

  const [selectedTier, setSelectedTier] = useState<MembershipTier>('free');
  const [tierDefaults, setTierDefaults] = useState<AllTierDefaults>({});
  const [globalProviders, setGlobalProviders] = useState<GlobalLLMProvider[]>([]);
  const [editingDefaults, setEditingDefaults] = useState<Partial<Record<MembershipTier, Partial<TierDefaults>>>>({});
  const [editingProviders, setEditingProviders] = useState<Record<string, GlobalLLMProvider>>({});
  const [loading, setLoading] = useState(true);
  const [showAddProviderModal, setShowAddProviderModal] = useState(false);
  const [newProvider, setNewProvider] = useState({
    provider_id: '',
    base_url: '',
    models: [{ name: '', min_tier: 'free' as MembershipTier }],
    enabled: true
  });

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (mounted && isAuthenticated && isAdmin) {
      loadAllData();
    } else if (mounted && !isAuthenticated) {
      setLoading(false);
    }
  }, [mounted, isAuthenticated, isAdmin]);

  const loadAllData = async () => {
    setLoading(true);
    try {
      const [defaults, providers] = await Promise.all([
        getAllTierDefaults(),
        getGlobalProviders()
      ]);
      setTierDefaults(defaults);
      setGlobalProviders(providers.providers);
    } catch (error) {
      console.error('Failed to load tier config:', error);
      showError('Failed to load configuration');
    } finally {
      setLoading(false);
    }
  };

  const handleSaveDefaults = async (tier: MembershipTier) => {
    try {
      const defaults = editingDefaults[tier];
      if (!defaults) return;

      await updateTierDefaults(tier, {
        default_chat_model: defaults.default_chat_model,
        default_writer_model: defaults.default_writer_model,
        article_limit_per_month: defaults.article_limit_per_month
      });

      showSuccess('Configuration saved');
      setEditingDefaults(prev => {
        const newState = { ...prev };
        delete newState[tier];
        return newState;
      });
      loadAllData();
    } catch (error) {
      console.error('Failed to save defaults:', error);
      showError('Failed to save');
    }
  };

  const handleSaveProvider = async (providerId: string) => {
    try {
      const provider = editingProviders[providerId];
      if (!provider) return;

      await updateGlobalProvider({
        provider_id: provider.provider_id,
        base_url: provider.base_url,
        models: provider.models,
        enabled: provider.enabled
      });

      showSuccess('Provider configuration saved');
      setEditingProviders(prev => {
        const newState = { ...prev };
        delete newState[providerId];
        return newState;
      });
      loadAllData();
    } catch (error) {
      console.error('Failed to save provider:', error);
      showError('Failed to save');
    }
  };

  const handleAddGlobalProvider = async () => {
    try {
      await updateGlobalProvider({
        ...newProvider,
        models: newProvider.models.filter(m => m.name.trim())
      });

      showSuccess('Provider added');
      setNewProvider({ provider_id: '', base_url: '', models: [{ name: '', min_tier: 'free' }], enabled: true });
      setShowAddProviderModal(false);
      loadAllData();
    } catch (error) {
      console.error('Failed to add provider:', error);
      showError('Failed to add');
    }
  };

  const handleDeleteProvider = async (providerId: string) => {
    if (!confirm('Are you sure you want to delete this provider?')) return;

    try {
      await deleteGlobalProvider(providerId);
      showSuccess('Provider deleted');
      loadAllData();
    } catch (error) {
      console.error('Failed to delete provider:', error);
      showError('Failed to delete');
    }
  };

  if (!mounted) {
    return (
      <MainLayout>
        <div className="max-w-6xl mx-auto">
          <div className="flex items-center justify-center py-12">
            <Loader2 className="animate-spin text-primary mr-4" size={48} />
          </div>
        </div>
      </MainLayout>
    );
  }

  if (!isAuthenticated || !isAdmin) {
    return (
      <MainLayout>
        <div className="max-w-6xl mx-auto">
          <div className="flex flex-col items-center justify-center py-12">
            <p className="text-text-secondary text-lg mb-4">Admin access required</p>
            <Button variant="primary" onClick={() => window.location.href = '/settings'}>
              Back to Settings
            </Button>
          </div>
        </div>
      </MainLayout>
    );
  }

  return (
    <MainLayout>
      <div className="max-w-6xl mx-auto">
        <div className="flex items-center gap-3 mb-8">
          <Settings size={32} />
          <div>
            <h1 className="font-heading text-[32px] font-semibold text-text-primary">
              Tier Configuration
            </h1>
            <p className="font-body text-base text-text-secondary mt-1">
              Configure tier default models, quotas, and global LLM provider model tiers
            </p>
          </div>
        </div>

        {loading ? (
          <Card padding="xl">
            <div className="flex flex-col items-center justify-center py-12">
              <Loader2 className="animate-spin text-primary mb-4" size={48} />
              <p className="text-text-secondary">Loading...</p>
            </div>
          </Card>
        ) : (
          <>
            {/* Tier Selection Tabs */}
            <div className="flex gap-2 mb-6">
              {TIERS.map(tier => (
                <button
                  key={tier}
                  onClick={() => setSelectedTier(tier)}
                  className={`h-10 px-5 rounded-lg font-body text-[15px] font-semibold transition-all ${
                    selectedTier === tier
                      ? 'bg-primary text-white'
                      : 'bg-transparent border-[1.5px] border-border text-text-secondary hover:border-primary'
                  }`}
                >
                  {TIER_NAMES[tier]}
                </button>
              ))}
            </div>

            {/* Tier Default Configuration */}
            <Card padding="xl" className="mb-6">
              <div className="flex items-center justify-between mb-6">
                <h3 className="font-heading text-lg font-semibold text-text-primary">
                  {TIER_NAMES[selectedTier]} - Default Configuration
                </h3>
                {editingDefaults[selectedTier] && (
                  <Button
                    size="sm"
                    onClick={() => handleSaveDefaults(selectedTier)}
                  >
                    <Save size={16} className="mr-2" />
                    Save
                  </Button>
                )}
              </div>

              <div className="grid grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-text-primary mb-2">
                    Default Chat Model
                  </label>
                  <Input
                    value={editingDefaults[selectedTier]?.default_chat_model ?? tierDefaults[selectedTier]?.default_chat_model ?? ''}
                    onChange={(e) => setEditingDefaults(prev => ({
                      ...prev,
                      [selectedTier]: {
                        ...prev[selectedTier],
                        default_chat_model: e.target.value,
                        article_limit_per_month: prev[selectedTier]?.article_limit_per_month ?? tierDefaults[selectedTier]?.article_limit_per_month ?? 0,
                        tier: selectedTier,
                        updated_at: new Date().toISOString()
                      }
                    }))}
                    placeholder="deepseek:deepseek-chat"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-text-primary mb-2">
                    Default Writer Model
                  </label>
                  <Input
                    value={editingDefaults[selectedTier]?.default_writer_model ?? tierDefaults[selectedTier]?.default_writer_model ?? ''}
                    onChange={(e) => setEditingDefaults(prev => ({
                      ...prev,
                      [selectedTier]: {
                        ...prev[selectedTier],
                        default_writer_model: e.target.value,
                        article_limit_per_month: prev[selectedTier]?.article_limit_per_month ?? tierDefaults[selectedTier]?.article_limit_per_month ?? 0,
                        tier: selectedTier,
                        updated_at: new Date().toISOString()
                      }
                    }))}
                    placeholder="deepseek:deepseek-chat"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-text-primary mb-2">
                    Monthly Article Quota
                  </label>
                  <Input
                    type="number"
                    value={editingDefaults[selectedTier]?.article_limit_per_month ?? tierDefaults[selectedTier]?.article_limit_per_month ?? 0}
                    onChange={(e) => setEditingDefaults(prev => ({
                      ...prev,
                      [selectedTier]: {
                        ...prev[selectedTier],
                        article_limit_per_month: parseInt(e.target.value) || 0,
                        default_chat_model: prev[selectedTier]?.default_chat_model ?? tierDefaults[selectedTier]?.default_chat_model ?? '',
                        default_writer_model: prev[selectedTier]?.default_writer_model ?? tierDefaults[selectedTier]?.default_writer_model ?? '',
                        tier: selectedTier,
                        updated_at: new Date().toISOString()
                      }
                    }))}
                    min="0"
                  />
                </div>
              </div>
            </Card>

            {/* Global LLM Providers Configuration */}
            <Card padding="xl" className="mb-6">
              <div className="flex items-center justify-between mb-6">
                <h3 className="font-heading text-lg font-semibold text-text-primary">
                  Global LLM Providers - Model Tier Configuration
                </h3>
                <Button
                  size="sm"
                  onClick={() => setShowAddProviderModal(true)}
                >
                  <Plus size={16} className="mr-2" />
                  Add Provider
                </Button>
              </div>

              <p className="text-sm text-text-secondary mb-4">
                Set the minimum tier (min_tier) for each model. Users can only use models where their tier is greater than or equal to min_tier.
              </p>

              <div className="space-y-6">
                {globalProviders.map(provider => {
                  const isEditing = !!editingProviders[provider.provider_id];
                  const currentProvider = editingProviders[provider.provider_id] ?? provider;

                  return (
                    <div key={provider.provider_id} className="p-4 bg-bg rounded-lg">
                      <div className="flex items-center justify-between mb-4">
                        <div className="flex items-center gap-3">
                          <span className="font-heading text-base font-semibold text-text-primary">
                            {provider.provider_name}
                          </span>
                          <Badge variant={provider.enabled ? 'success' : 'secondary'}>
                            {provider.enabled ? 'Enabled' : 'Disabled'}
                          </Badge>
                        </div>
                        <div className="flex gap-2">
                          {isEditing && (
                            <Button
                              size="sm"
                              onClick={() => handleSaveProvider(provider.provider_id)}
                            >
                              <Save size={14} className="mr-1" />
                              Save
                            </Button>
                          )}
                          <Button
                            variant="secondary"
                            size="sm"
                            onClick={() => handleDeleteProvider(provider.provider_id)}
                          >
                            <Trash2 size={14} />
                          </Button>
                        </div>
                      </div>

                      <div className="grid grid-cols-2 gap-4 mb-4">
                        <div>
                          <label className="block text-sm font-medium text-text-primary mb-1">
                            Base URL
                          </label>
                          <Input
                            value={currentProvider.base_url}
                            onChange={(e) => setEditingProviders(prev => ({
                              ...prev,
                              [provider.provider_id]: {
                                ...currentProvider,
                                base_url: e.target.value
                              }
                            }))}
                            placeholder="https://api.deepseek.com"
                          />
                        </div>
                        <div className="flex items-end">
                          <label className="flex items-center gap-2">
                            <input
                              type="checkbox"
                              checked={currentProvider.enabled}
                              onChange={(e) => setEditingProviders(prev => ({
                                ...prev,
                                [provider.provider_id]: {
                                  ...currentProvider,
                                  enabled: e.target.checked
                                }
                              }))}
                              className="rounded"
                            />
                            <span className="text-sm">Enabled</span>
                          </label>
                        </div>
                      </div>

                      {/* Model List */}
                      <div className="space-y-2">
                        <label className="block text-sm font-medium text-text-primary">
                          Model Configuration
                        </label>
                        {currentProvider.models.map((model, idx) => (
                          <div key={idx} className="flex items-center gap-3">
                            <Input
                              value={model.name}
                              onChange={(e) => {
                                const newModels = [...currentProvider.models];
                                newModels[idx] = { ...newModels[idx], name: e.target.value };
                                setEditingProviders(prev => ({
                                  ...prev,
                                  [provider.provider_id]: {
                                    ...currentProvider,
                                    models: newModels
                                  }
                                }));
                              }}
                              placeholder="Model name"
                              className="flex-1"
                            />
                            <select
                              value={model.min_tier}
                              onChange={(e) => {
                                const newModels = [...currentProvider.models];
                                newModels[idx] = { ...newModels[idx], min_tier: e.target.value as MembershipTier };
                                setEditingProviders(prev => ({
                                  ...prev,
                                  [provider.provider_id]: {
                                    ...currentProvider,
                                    models: newModels
                                  }
                                }));
                              }}
                              className="h-10 px-3 rounded-lg border border-border bg-bg-alt text-text-primary"
                            >
                              {TIERS.map(tier => (
                                <option key={tier} value={tier}>{TIER_NAMES[tier]}</option>
                              ))}
                            </select>
                            <button
                              onClick={() => {
                                const newModels = currentProvider.models.filter((_, i) => i !== idx);
                                setEditingProviders(prev => ({
                                  ...prev,
                                  [provider.provider_id]: {
                                    ...currentProvider,
                                    models: newModels
                                  }
                                }));
                              }}
                              className="p-2 text-red-500 hover:text-red-700"
                            >
                              <Trash2 size={16} />
                            </button>
                          </div>
                        ))}
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={() => {
                            setEditingProviders(prev => ({
                              ...prev,
                              [provider.provider_id]: {
                                ...currentProvider,
                                models: [...currentProvider.models, { name: '', min_tier: 'free' as MembershipTier }]
                              }
                            }));
                          }}
                        >
                          <Plus size={14} className="mr-1" />
                          Add Model
                        </Button>
                      </div>
                    </div>
                  );
                })}
              </div>
            </Card>
          </>
        )}

        {/* Add Provider Modal */}
        {showAddProviderModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <Card padding="xl" className="w-full max-w-lg">
              <h3 className="font-heading text-lg font-semibold text-text-primary mb-4">
                Add LLM Provider
              </h3>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-text-primary mb-1">
                    Provider ID
                  </label>
                  <Input
                    value={newProvider.provider_id}
                    onChange={(e) => setNewProvider(prev => ({ ...prev, provider_id: e.target.value }))}
                    placeholder="deepseek"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-text-primary mb-1">
                    Base URL
                  </label>
                  <Input
                    value={newProvider.base_url}
                    onChange={(e) => setNewProvider(prev => ({ ...prev, base_url: e.target.value }))}
                    placeholder="https://api.deepseek.com"
                  />
                </div>
                <div className="flex gap-2 justify-end">
                  <Button variant="secondary" onClick={() => setShowAddProviderModal(false)}>
                    Cancel
                  </Button>
                  <Button onClick={handleAddGlobalProvider}>
                    Add
                  </Button>
                </div>
              </div>
            </Card>
          </div>
        )}
      </div>
    </MainLayout>
  );
}
